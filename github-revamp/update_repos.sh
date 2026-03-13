#!/bin/bash
# =============================================================================
# Push new READMEs to ALL repos for thisisyoussef
# Requires: git authenticated with GitHub (SSH or HTTPS token)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
READMES_DIR="$SCRIPT_DIR/readmes"
TEMP_DIR=$(mktemp -d)
SUCCESS=0
FAIL=0

echo "🚀 Pushing README updates to GitHub..."
echo "   Working in: $TEMP_DIR"
echo ""

update_repo() {
    local repo=$1
    local readme_file=$2

    echo "📝 $repo..."
    cd "$TEMP_DIR"

    if ! git clone --depth 1 "https://github.com/thisisyoussef/$repo.git" "$repo" 2>/dev/null; then
        echo "   ⚠️  Failed to clone — skipping"
        FAIL=$((FAIL + 1))
        return 0
    fi

    cd "$repo"
    local default_branch
    default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

    cp "$READMES_DIR/$readme_file" README.md
    git add README.md
    if git commit -m "Add project documentation" 2>/dev/null; then
        if git push origin "$default_branch" 2>/dev/null; then
            echo "   ✅ Done"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "   ⚠️  Push failed"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "   — No changes needed"
    fi
}

# ═══════════════════════════════════════════
# PROFILE README
# ═══════════════════════════════════════════
echo "═══ Profile README ═══"
cd "$TEMP_DIR"
git clone --depth 1 "https://github.com/thisisyoussef/thisisyoussef.git" profile-repo 2>/dev/null
cp "$SCRIPT_DIR/PROFILE_README.md" profile-repo/README.md
cd profile-repo
git add README.md
git commit -m "Revamp profile README" 2>/dev/null && git push 2>/dev/null && echo "   ✅ Profile README" || echo "   ⚠️  Profile README failed"
echo ""

# ═══════════════════════════════════════════
# SHOWCASE PROJECTS (detailed READMEs with Mermaid diagrams)
# ═══════════════════════════════════════════
echo "═══ Showcase Projects ═══"
update_repo "event-scribe-ai-assist" "event-scribe-ai-assist_README.md"
update_repo "PLCProgrammingLanguage" "PLCProgrammingLanguage_README.md"
update_repo "exquizite" "exquizite_README.md"
update_repo "stevo_flutter" "stevo_flutter_README.md"
update_repo "instad" "instad_README.md"
update_repo "sawa" "sawa_README.md"
update_repo "MemoryManager" "MemoryManager_README.md"
update_repo "pocketpay" "pocketpay_README.md"
echo ""

# Note: procurement-ai README is ready but repo may need to be created first
echo "📝 Note: procurement-ai README at $READMES_DIR/procurement-ai_README.md"
echo "   Create the repo first if it doesn't exist on GitHub yet."
echo ""

# ═══════════════════════════════════════════
# INSTAD ECOSYSTEM
# ═══════════════════════════════════════════
echo "═══ Instad Ecosystem ═══"
update_repo "instad_user" "instad_user_README.md"
update_repo "instad_venue" "instad_venue_README.md"
echo ""

# ═══════════════════════════════════════════
# MID-TIER PROJECTS
# ═══════════════════════════════════════════
echo "═══ Mid-Tier Projects ═══"
update_repo "kafka-tutorial" "kafka-tutorial_README.md"
update_repo "jaeger-tracing" "jaeger-tracing_README.md"
update_repo "aqius" "aqius_README.md"
update_repo "job_search" "job_search_README.md"
update_repo "localization_task" "localization_task_README.md"
echo ""

# ═══════════════════════════════════════════
# FLUTTER BOOTCAMP
# ═══════════════════════════════════════════
echo "═══ Flutter Bootcamp ═══"
update_repo "bitcoin-flutter-final" "bitcoin-flutter-final_README.md"
update_repo "Clima-Flutter" "Clima-Flutter_README.md"
update_repo "flash-chat" "flash-chat_README.md"
update_repo "magic-8-ball-flutter" "magic-8-ball-flutter_README.md"
update_repo "bmi-calculator-flutter" "bmi-calculator-flutter_README.md"
update_repo "dicee-flutter" "dicee-flutter_README.md"
update_repo "xylophone-flutter" "xylophone-flutter_README.md"
echo ""

# ═══════════════════════════════════════════
# SMALLER PROJECTS & COURSEWORK
# ═══════════════════════════════════════════
echo "═══ Smaller Projects ═══"
update_repo "NutrientHelper" "NutrientHelper_README.md"
update_repo "NutritionListProject" "NutritionListProject_README.md"
update_repo "Pakudex" "Pakudex_README.md"
update_repo "SciCalculator" "SciCalculator_README.md"
update_repo "LinkedList" "LinkedList_README.md"
update_repo "task-manager" "task-manager_README.md"
update_repo "notes-app" "notes-app_README.md"
update_repo "weather_website" "weather_website_README.md"
update_repo "InstaBugTask" "InstaBugTask_README.md"
update_repo "todoapp" "todoapp_README.md"
update_repo "tamas" "tamas_README.md"
update_repo "qintarapp" "qintarapp_README.md"
update_repo "iOS-101-Prework" "iOS-101-Prework_README.md"
echo ""

# ═══════════════════════════════════════════
rm -rf "$TEMP_DIR"
echo "============================================"
echo "🎉 Done! $SUCCESS updated, $FAIL skipped."
echo ""
echo "Next steps:"
echo "  1. bash update_descriptions.sh   (repo descriptions + topics)"
echo "  2. Pin your top 6 at https://github.com/thisisyoussef"
echo "  3. Update bio at https://github.com/settings/profile"
echo "============================================"
