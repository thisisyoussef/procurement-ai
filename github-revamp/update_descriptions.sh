#!/bin/bash
# =============================================================================
# Update ALL repo descriptions and topics for thisisyoussef
# Requires: gh CLI authenticated (run: gh auth login)
# =============================================================================

set -e
echo "📝 Updating repo descriptions and topics..."
echo ""

# ──────────────────────────────────────────────────
# PINNED REPOS (the showcase — descriptions matter most here)
# ──────────────────────────────────────────────────

gh repo edit thisisyoussef/event-scribe-ai-assist \
  --description "Community event management platform with AI-assisted creation, volunteer tracking & analytics. In production. React + TypeScript + Supabase + OpenAI." \
  --add-topic "react" --add-topic "typescript" --add-topic "supabase" --add-topic "openai" --add-topic "tailwindcss" --add-topic "shadcn-ui" --add-topic "event-management" --add-topic "ai" --add-topic "volunteer-management" --add-topic "production"

gh repo edit thisisyoussef/procurement-ai \
  --description "AI agent that discovers, verifies & compares suppliers for small businesses. 5-agent LangGraph pipeline with cost-optimized Claude routing." \
  --add-topic "python" --add-topic "fastapi" --add-topic "langgraph" --add-topic "anthropic" --add-topic "claude" --add-topic "ai-agents" --add-topic "nextjs" --add-topic "procurement" --add-topic "multi-agent"

gh repo edit thisisyoussef/PLCProgrammingLanguage \
  --description "Full programming language compiler: lexer → parser → AST → type checker → code generator with in-memory Java bytecode compilation." \
  --add-topic "java" --add-topic "compiler" --add-topic "programming-language" --add-topic "lexer" --add-topic "parser" --add-topic "ast" --add-topic "type-checker" --add-topic "code-generation" --add-topic "bytecode"

gh repo edit thisisyoussef/exquizite \
  --description "Assessment platform that auto-generates quiz questions from PDFs/Word/Excel. Async Bull/Redis processing, real-time Socket.io quiz sessions." \
  --add-topic "nodejs" --add-topic "express" --add-topic "mongodb" --add-topic "redis" --add-topic "bull-queue" --add-topic "socketio" --add-topic "quiz" --add-topic "document-processing" --add-topic "passport"

gh repo edit thisisyoussef/stevo_flutter \
  --description "AI-powered adaptive learning platform — GPT generates personalized lessons & assessments. Real-time sync via Socket.io + Redis caching." \
  --add-topic "flutter" --add-topic "dart" --add-topic "openai" --add-topic "education" --add-topic "mobile-app" --add-topic "socketio" --add-topic "redis" --add-topic "ai" --add-topic "cross-platform"

gh repo edit thisisyoussef/instad \
  --description "Sports venue discovery & booking platform — core library for the 3-app Instad ecosystem. Flutter + Google Maps + Firebase." \
  --add-topic "flutter" --add-topic "dart" --add-topic "google-maps" --add-topic "firebase" --add-topic "mobile-app" --add-topic "booking" --add-topic "sports" --add-topic "marketplace"

# ──────────────────────────────────────────────────
# INSTAD ECOSYSTEM
# ──────────────────────────────────────────────────

gh repo edit thisisyoussef/instad_user \
  --description "Athlete-facing app for discovering and booking sports venues. Part of the Instad 3-app ecosystem. Flutter + Dart + Google Maps." \
  --add-topic "flutter" --add-topic "dart" --add-topic "google-maps" --add-topic "firebase" --add-topic "mobile-app"

gh repo edit thisisyoussef/instad_venue \
  --description "Venue owner app for managing listings, availability & bookings. Part of the Instad 3-app ecosystem. Flutter + Dart." \
  --add-topic "flutter" --add-topic "dart" --add-topic "firebase" --add-topic "mobile-app" --add-topic "booking-management"

# ──────────────────────────────────────────────────
# OTHER NOTABLE PROJECTS
# ──────────────────────────────────────────────────

gh repo edit thisisyoussef/sawa \
  --description "Custom apparel e-commerce platform with product customization, scroll-driven animations & clean architecture. Flutter 3 + Supabase." \
  --add-topic "flutter" --add-topic "dart" --add-topic "ecommerce" --add-topic "clean-architecture" --add-topic "supabase" --add-topic "web-app"

gh repo edit thisisyoussef/MemoryManager \
  --description "Custom memory allocator in C++ — doubly linked list with best-fit/worst-fit strategies, hole coalescing, and sbrk() allocation." \
  --add-topic "cpp" --add-topic "memory-management" --add-topic "operating-systems" --add-topic "data-structures" --add-topic "systems-programming"

gh repo edit thisisyoussef/pocketpay \
  --description "Payment processing backend with dual user/merchant system — onboarding, verification, payments, receipts, refunds. Node.js + Express + MongoDB." \
  --add-topic "nodejs" --add-topic "express" --add-topic "mongodb" --add-topic "payments" --add-topic "api" --add-topic "fintech"

gh repo edit thisisyoussef/aqius \
  --description "Lightweight data visualization mobile app with interactive charts and filtering. Flutter + Dart." \
  --add-topic "flutter" --add-topic "dart" --add-topic "data-visualization" --add-topic "mobile-app"

gh repo edit thisisyoussef/job_search \
  --description "Cross-platform job search app with filters, favorites & detailed listings. Flutter + Dart." \
  --add-topic "flutter" --add-topic "dart" --add-topic "mobile-app" --add-topic "job-search"

gh repo edit thisisyoussef/localization_task \
  --description "Flutter localization demo with runtime language switching and JSON-based translations." \
  --add-topic "flutter" --add-topic "dart" --add-topic "localization" --add-topic "i18n"

gh repo edit thisisyoussef/kafka-tutorial \
  --description "Apache Kafka producer/consumer examples in Java — callbacks, key-based partitioning, consumer groups." \
  --add-topic "java" --add-topic "kafka" --add-topic "streaming" --add-topic "distributed-systems"

gh repo edit thisisyoussef/jaeger-tracing \
  --description "Distributed tracing setup with Jaeger for microservices observability." \
  --add-topic "javascript" --add-topic "jaeger" --add-topic "tracing" --add-topic "observability" --add-topic "microservices"

# ──────────────────────────────────────────────────
# SMALLER PROJECTS (still worth having clean descriptions)
# ──────────────────────────────────────────────────

gh repo edit thisisyoussef/pocketpayDomain \
  --description "Domain models and business logic for the PocketPay payment platform."

gh repo edit thisisyoussef/task-manager \
  --description "Task management app built with Node.js and Express." \
  --add-topic "nodejs" --add-topic "javascript"

gh repo edit thisisyoussef/notes-app \
  --description "Notes application built with Node.js." \
  --add-topic "nodejs" --add-topic "javascript"

gh repo edit thisisyoussef/weather_website \
  --description "Weather lookup website using a weather API. JavaScript + Node.js." \
  --add-topic "javascript" --add-topic "api" --add-topic "weather"

gh repo edit thisisyoussef/InstaBugTask \
  --description "Technical assessment project for Instabug. JavaScript." \
  --add-topic "javascript"

gh repo edit thisisyoussef/SciCalculator \
  --description "Scientific calculator built with Java." \
  --add-topic "java"

gh repo edit thisisyoussef/Pakudex \
  --description "Pokemon-inspired creature collection system built in Java." \
  --add-topic "java"

gh repo edit thisisyoussef/NutrientHelper \
  --description "Nutrient tracking and analysis tool built in C++." \
  --add-topic "cpp"

gh repo edit thisisyoussef/NutritionListProject \
  --description "Nutrition data management project in C++." \
  --add-topic "cpp"

gh repo edit thisisyoussef/tamas \
  --description "Flutter mobile application." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/qintarapp \
  --description "Flutter mobile application." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/todoapp \
  --description "Todo application built with Flutter." \
  --add-topic "flutter" --add-topic "dart"

# ──────────────────────────────────────────────────
# COURSEWORK / TUTORIALS (brief, honest descriptions)
# ──────────────────────────────────────────────────

gh repo edit thisisyoussef/LinkedList \
  --description "Linked list implementation in C++." \
  --add-topic "cpp" --add-topic "data-structures"

gh repo edit thisisyoussef/InheritanceLab \
  --description "OOP inheritance patterns in C++." \
  --add-topic "cpp"

gh repo edit thisisyoussef/ColorBinaryToHex \
  --description "Binary to hex color converter in C++." \
  --add-topic "cpp"

gh repo edit thisisyoussef/BinaryFileIO \
  --description "Binary file I/O operations in C++." \
  --add-topic "cpp"

gh repo edit thisisyoussef/ABSABQ \
  --description "C++ project." \
  --add-topic "cpp"

gh repo edit thisisyoussef/Project2 \
  --description "C programming project." \
  --add-topic "c"

gh repo edit thisisyoussef/iOS-101-Prework \
  --description "CodePath iOS 101 prework assignment. Swift." \
  --add-topic "swift" --add-topic "ios"

gh repo edit thisisyoussef/bitcoin-flutter-final \
  --description "Bitcoin price tracker built with Flutter." \
  --add-topic "flutter" --add-topic "dart" --add-topic "cryptocurrency"

gh repo edit thisisyoussef/Clima-Flutter \
  --description "Weather app built with Flutter — location-based forecasts." \
  --add-topic "flutter" --add-topic "dart" --add-topic "weather"

gh repo edit thisisyoussef/flash-chat \
  --description "Real-time chat app built with Flutter + Firebase." \
  --add-topic "flutter" --add-topic "dart" --add-topic "firebase"

gh repo edit thisisyoussef/magic-8-ball-flutter \
  --description "Magic 8-Ball app built with Flutter." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/bmi-calculator-flutter \
  --description "BMI calculator app built with Flutter." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/dicee-flutter \
  --description "Dice rolling app built with Flutter." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/xylophone-flutter \
  --description "Musical xylophone app built with Flutter." \
  --add-topic "flutter" --add-topic "dart"

gh repo edit thisisyoussef/codespace-test \
  --description "GitHub Codespaces test project." \

echo ""
echo "✅ All repo descriptions and topics updated!"
echo ""
echo "📌 Now pin your repos. Go to https://github.com/thisisyoussef"
echo "   Click 'Customize your pins' and select these 6 in order:"
echo "   1. event-scribe-ai-assist  (production app)"
echo "   2. procurement-ai          (AI agents)"
echo "   3. PLCProgrammingLanguage  (compiler — CS depth)"
echo "   4. exquizite               (full-stack backend)"
echo "   5. stevo_flutter           (mobile + AI)"
echo "   6. instad                  (multi-app ecosystem)"
