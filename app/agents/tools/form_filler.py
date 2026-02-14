"""Web form detection, analysis, filling, and submission via Browserbase + Playwright.

Adds "web form" as a third outreach channel alongside email and phone calls.
Detects quote/contact forms on supplier websites, maps RFQ fields to form inputs,
fills them via Playwright, and submits.

Pipeline:
1. Form Discovery — find "Get a Quote" / "Contact Us" links
2. Form Analysis — extract form fields via DOM
3. Field Mapping — LLM maps RFQ data to form fields
4. Form Filling — Playwright fills fields
5. Submission — click submit, capture confirmation
"""

import asyncio
import base64
import json
import logging
import re
from urllib.parse import urlparse, urljoin

from pydantic import BaseModel, Field

from app.agents.tools.browserbase_service import (
    _with_page,
    _is_configured,
    _dismiss_cookie_banner,
    _scroll_page,
    PAGE_LOAD_TIMEOUT_MS,
)
from app.core.config import get_settings
from app.core.llm_gateway import call_llm_structured
from app.schemas.agent_state import FormFillResult

settings = get_settings()
logger = logging.getLogger(__name__)

# Common CTA text patterns for quote/contact forms
FORM_LINK_PATTERNS = [
    "Get a Quote", "Request Quote", "Request a Quote",
    "Get Quote", "RFQ", "Request for Quote",
    "Contact Us", "Contact", "Get in Touch",
    "Inquiry", "Enquiry", "Send Inquiry",
    "Request Pricing", "Get Pricing",
    "Request Sample", "Request Information",
]


class FormField(BaseModel):
    """A detected form field."""
    selector: str
    field_type: str  # text, email, tel, textarea, select, checkbox, radio
    name: str = ""
    label: str = ""
    placeholder: str = ""
    required: bool = False
    options: list[str] = Field(default_factory=list)  # for select/radio


class DetectedForm(BaseModel):
    """A detected quote/contact form on a supplier website."""
    form_url: str
    form_selector: str = "form"
    fields: list[FormField] = Field(default_factory=list)
    submit_selector: str = ""
    screenshot_b64: str | None = None


# JavaScript to extract form fields from the current page
_EXTRACT_FORM_JS = """
() => {
    // Find the most relevant form (prefer forms with keywords in action/class/id)
    const forms = document.querySelectorAll('form');
    let bestForm = null;
    const keywords = ['quote', 'contact', 'inquiry', 'rfq', 'enquiry', 'pricing'];

    for (const form of forms) {
        const formText = (form.action + ' ' + form.className + ' ' + form.id + ' ' +
                          form.innerHTML.substring(0, 500)).toLowerCase();
        const hasKeyword = keywords.some(k => formText.includes(k));
        if (hasKeyword || !bestForm) {
            bestForm = form;
            if (hasKeyword) break;
        }
    }

    if (!bestForm) return null;

    // Build a unique CSS selector for the form
    let formSelector = 'form';
    if (bestForm.id) formSelector = `form#${bestForm.id}`;
    else if (bestForm.className) {
        const cls = bestForm.className.split(' ')[0];
        if (cls) formSelector = `form.${cls}`;
    }

    // Extract fields
    const fields = [];
    const inputs = bestForm.querySelectorAll('input, textarea, select');

    for (const input of inputs) {
        const type = input.tagName.toLowerCase() === 'textarea' ? 'textarea'
            : input.tagName.toLowerCase() === 'select' ? 'select'
            : (input.type || 'text');

        // Skip hidden and submit inputs
        if (type === 'hidden' || type === 'submit' || type === 'button') continue;

        // Build a selector for this field
        let selector = '';
        if (input.id) selector = `#${input.id}`;
        else if (input.name) selector = `${formSelector} [name="${input.name}"]`;
        else {
            const idx = Array.from(inputs).indexOf(input);
            selector = `${formSelector} :nth-child(${idx + 1})`;
        }

        // Find associated label
        let label = '';
        if (input.id) {
            const labelEl = document.querySelector(`label[for="${input.id}"]`);
            if (labelEl) label = labelEl.textContent.trim();
        }
        if (!label) {
            const parent = input.closest('label, .form-group, .field, [class*="field"]');
            if (parent) {
                const labelEl = parent.querySelector('label, .label, span');
                if (labelEl && labelEl !== input) label = labelEl.textContent.trim();
            }
        }

        // Get select options
        const options = [];
        if (type === 'select') {
            const opts = input.querySelectorAll('option');
            opts.forEach(opt => {
                if (opt.value) options.push(opt.textContent.trim());
            });
        }

        fields.push({
            selector,
            field_type: type,
            name: input.name || '',
            label: label || input.placeholder || input.name || '',
            placeholder: input.placeholder || '',
            required: input.required || false,
            options,
        });
    }

    // Find submit button
    let submitSelector = '';
    const submitBtn = bestForm.querySelector(
        'button[type="submit"], input[type="submit"], button:not([type])'
    );
    if (submitBtn) {
        if (submitBtn.id) submitSelector = `#${submitBtn.id}`;
        else submitSelector = `${formSelector} button[type="submit"], ${formSelector} input[type="submit"], ${formSelector} button:not([type])`;
    }

    return {
        formSelector,
        fields,
        submitSelector,
    };
}
"""


async def detect_form(website_url: str) -> DetectedForm | None:
    """Detect a quote/contact form on a supplier's website.

    Strategy:
    1. Navigate to homepage
    2. Search for quote/contact form links
    3. Click through to form page
    4. Extract form fields via DOM analysis

    Args:
        website_url: The supplier's website URL.

    Returns:
        DetectedForm with field details, or None if no form found.
    """
    if not _is_configured():
        logger.debug("Browserbase not configured — skipping form detection")
        return None

    logger.info("  [FormFiller] Detecting forms on: %s", website_url)

    async def _detect(page):
        # Navigate to homepage
        await page.goto(
            website_url,
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )
        await _dismiss_cookie_banner(page)

        # Try to find and click a quote/contact link
        form_page_url = website_url
        for pattern in FORM_LINK_PATTERNS:
            try:
                link = page.get_by_role(
                    "link", name=re.compile(pattern, re.IGNORECASE)
                ).first
                href = await link.get_attribute("href", timeout=1500)
                if href:
                    # Resolve relative URL
                    if href.startswith("/"):
                        parsed = urlparse(website_url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    elif not href.startswith("http"):
                        href = website_url.rstrip("/") + "/" + href

                    await page.goto(
                        href,
                        wait_until="networkidle",
                        timeout=PAGE_LOAD_TIMEOUT_MS,
                    )
                    form_page_url = href
                    logger.info("  [FormFiller] Navigated to form page: %s", href)
                    break
            except Exception:
                continue

        # Also try clicking buttons with quote/contact text
        if form_page_url == website_url:
            for pattern in FORM_LINK_PATTERNS[:6]:  # Focus on quote-related
                try:
                    btn = page.get_by_role(
                        "button", name=re.compile(pattern, re.IGNORECASE)
                    ).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click(timeout=2000)
                        await page.wait_for_timeout(1500)
                        form_page_url = page.url
                        logger.info("  [FormFiller] Clicked form button, now at: %s", form_page_url)
                        break
                except Exception:
                    continue

        # Extract form fields via JavaScript
        raw = await page.evaluate(_EXTRACT_FORM_JS)

        if not raw or not raw.get("fields"):
            logger.info("  [FormFiller] No form detected on %s", form_page_url)
            return None

        # Take screenshot of the form
        screenshot = await page.screenshot(full_page=False, type="png")
        screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")

        fields = [FormField(**f) for f in raw["fields"]]
        logger.info(
            "  [FormFiller] Detected form with %d fields on %s",
            len(fields), form_page_url,
        )

        return DetectedForm(
            form_url=form_page_url,
            form_selector=raw.get("formSelector", "form"),
            fields=fields,
            submit_selector=raw.get("submitSelector", ""),
            screenshot_b64=screenshot_b64,
        )

    return await _with_page(_detect)


async def map_fields_to_rfq(
    form: DetectedForm,
    rfq_data: dict,
) -> dict[str, str]:
    """Use LLM to map RFQ data to detected form fields.

    Args:
        form: The detected form with field details.
        rfq_data: Dict with keys like product_type, quantity, company_name, email, etc.

    Returns:
        Dict mapping field selectors to values to fill.
    """
    fields_desc = []
    for f in form.fields:
        desc = f"- Selector: {f.selector} | Type: {f.field_type} | Label: {f.label}"
        if f.placeholder:
            desc += f" | Placeholder: {f.placeholder}"
        if f.name:
            desc += f" | Name: {f.name}"
        if f.required:
            desc += " | REQUIRED"
        if f.options:
            desc += f" | Options: {', '.join(f.options[:10])}"
        fields_desc.append(desc)

    prompt = f"""Map this RFQ data to the form fields below. Return a JSON object where
keys are the field CSS selectors and values are what to fill in.

## RFQ Data
{json.dumps(rfq_data, indent=2)}

## Form Fields
{chr(10).join(fields_desc)}

Rules:
- Only include fields you can confidently map. Skip fields you're unsure about.
- For "select" fields, use one of the available options that best matches.
- For "textarea" fields with product description, write a professional inquiry message.
- For "checkbox" fields, use "true" if it should be checked.
- Use professional, concise language.

Return ONLY a JSON object like: {{"#field-selector": "value to fill", ...}}"""

    response = await call_llm_structured(
        prompt=prompt,
        system="You map procurement RFQ data to web form fields. Return only valid JSON.",
        model=settings.model_cheap,
        max_tokens=1000,
    )

    try:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        mapping = json.loads(text)
        logger.info("  [FormFiller] Mapped %d fields", len(mapping))
        return mapping
    except json.JSONDecodeError:
        logger.warning("  [FormFiller] Failed to parse field mapping")
        return {}


async def fill_and_submit_form(
    website_url: str,
    rfq_data: dict,
    supplier_name: str,
    supplier_index: int,
    auto_submit: bool = False,
) -> FormFillResult:
    """Complete form-filling pipeline: detect → map → fill → (optionally) submit.

    Args:
        website_url: Supplier's website URL.
        rfq_data: RFQ data to fill (product_type, quantity, email, company_name, etc.)
        supplier_name: Name of the supplier (for logging/tracking).
        supplier_index: Index in the supplier list.
        auto_submit: If True, automatically submit the form. If False, fill only.

    Returns:
        FormFillResult with status and screenshots.
    """
    result = FormFillResult(
        supplier_name=supplier_name,
        supplier_index=supplier_index,
    )

    if not _is_configured():
        result.status = "failed"
        result.error = "Browserbase not configured"
        return result

    # Step 1: Detect form
    form = await detect_form(website_url)
    if not form:
        result.status = "failed"
        result.error = "No quote/contact form detected on website"
        return result

    result.form_url = form.form_url
    result.status = "form_detected"
    result.fields_total = len(form.fields)
    result.screenshot_before_b64 = form.screenshot_b64

    # Step 2: Map fields
    field_mapping = await map_fields_to_rfq(form, rfq_data)
    if not field_mapping:
        result.status = "failed"
        result.error = "Could not map RFQ data to form fields"
        return result

    result.fields_filled = len(field_mapping)
    result.status = "filling"

    # Step 3: Fill and optionally submit
    logger.info(
        "  [FormFiller] Filling %d fields on %s for %s",
        len(field_mapping), form.form_url, supplier_name,
    )

    async def _fill(page):
        # Navigate to the form page
        await page.goto(
            form.form_url,
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT_MS,
        )
        await _dismiss_cookie_banner(page)

        # Fill each mapped field
        filled = 0
        for selector, value in field_mapping.items():
            try:
                el = page.locator(selector).first
                if not await el.is_visible(timeout=2000):
                    logger.debug("  [FormFiller] Field not visible: %s", selector)
                    continue

                tag = await el.evaluate("el => el.tagName.toLowerCase()")

                if tag == "select":
                    await el.select_option(label=value, timeout=3000)
                elif tag == "textarea":
                    await el.fill(value, timeout=3000)
                elif tag == "input":
                    input_type = await el.get_attribute("type") or "text"
                    if input_type == "checkbox":
                        if value.lower() in ("true", "yes", "1"):
                            await el.check(timeout=2000)
                    elif input_type == "radio":
                        await el.check(timeout=2000)
                    else:
                        await el.fill(value, timeout=3000)
                else:
                    await el.fill(value, timeout=3000)

                filled += 1
                logger.debug("  [FormFiller] Filled %s = %s", selector, value[:50])
            except Exception as e:
                logger.warning("  [FormFiller] Failed to fill %s: %s", selector, e)

        result.fields_filled = filled

        # Take screenshot of filled form
        screenshot_after = await page.screenshot(full_page=False, type="png")
        result.screenshot_after_b64 = base64.b64encode(screenshot_after).decode("utf-8")

        if auto_submit and form.submit_selector:
            try:
                submit_btn = page.locator(form.submit_selector).first
                if await submit_btn.is_visible(timeout=2000):
                    await submit_btn.click(timeout=5000)
                    await page.wait_for_timeout(3000)

                    # Check for confirmation
                    confirmation = await page.evaluate("""
                        () => {
                            const text = document.body.innerText;
                            const patterns = [
                                'thank you', 'thanks', 'submitted', 'received',
                                'confirmation', 'success', 'sent'
                            ];
                            for (const p of patterns) {
                                if (text.toLowerCase().includes(p)) {
                                    // Get surrounding context
                                    const idx = text.toLowerCase().indexOf(p);
                                    return text.substring(Math.max(0, idx - 50), idx + 100).trim();
                                }
                            }
                            return null;
                        }
                    """)

                    if confirmation:
                        result.status = "confirmed"
                        result.confirmation_text = confirmation
                    else:
                        result.status = "submitted"

                    # Final screenshot
                    final_screenshot = await page.screenshot(full_page=False, type="png")
                    result.screenshot_after_b64 = base64.b64encode(final_screenshot).decode("utf-8")

                    logger.info(
                        "  [FormFiller] Form submitted for %s (status: %s)",
                        supplier_name, result.status,
                    )
                else:
                    result.status = "filled"
                    logger.info("  [FormFiller] Submit button not visible for %s", supplier_name)
            except Exception as e:
                result.status = "filled"
                result.error = f"Submit failed: {str(e)}"
                logger.warning("  [FormFiller] Submit failed for %s: %s", supplier_name, e)
        else:
            result.status = "filled"

        return result

    fill_result = await _with_page(_fill)

    if fill_result is None:
        result.status = "failed"
        result.error = "Browser session failed during form filling"
        return result

    return fill_result
