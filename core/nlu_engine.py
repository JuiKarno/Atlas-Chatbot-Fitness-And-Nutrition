import json
from openai import OpenAI
from config.settings import Config


class SmartNLUEngine:
    def __init__(self):
        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=Config.OPENROUTER_API_KEY,
        )

    def analyze_message(self, message, chat_history):
        """
        Analyzes the user message to determine intent and extract entities.
        Optimized to detect preferences, feedback, vague queries, and out-of-scope topics.
        """
        system_prompt = """
        You are the NLU brain for 'Atlas', a specialized AI Fitness & Nutrition Coach.
        Your Scope: STRICTLY Fitness, Exercise, Nutrition, Diet, Health, and Recovery.

        ### PRIORITY RULES (Check in this exact order!)
        1. **PREFERENCE DETECTION (Check FIRST)**
           - If message contains "I like", "I love", "I prefer", "I enjoy", "I'm a fan of" → `add_preference`
           - If message contains "I hate", "I dislike", "I don't like", "not a fan of", "avoid", "no [food/exercise]" → `add_dislike`
           - If message asks to "clear", "reset", or "remove" preferences → `clear_preferences`
        
        2. **COACH INTERVENTION (Check SECOND)**
           - If user wants to "dislike", "avoid", "skip", or "hate" a Gold Standard item (Squats, Deadlifts, Burpees, HIIT, High Protein) → `coach_challenge`
           - If user makes excuses like "it's too hard", "I'm tired", "don't like it" regarding top-tier exercises → `coach_challenge`
        
        3. **HEALTH QUESTIONS (Check THIRD - VERY IMPORTANT)**
           - If message asks to "give me", "suggest", "recommend", "show me", "what should I" → recommendation intent
           - If message has a question about how to do something → `explain_exercise`
        
        4. **FALLBACK** → Use other intents below

        ### INTENT LIST (Pick ONE)
        - 'add_preference': User states what they LIKE. Keywords: "I like", "I love", "I prefer", "I enjoy"
        - 'add_dislike': User states what they DISLIKE. Keywords: "I hate", "I dislike", "I don't like", "avoid"
        - 'clear_preferences': User wants to RESET likes/dislikes.
        - 'general_chat': Greetings, motivation, OR **Health/Fitness QUESTIONS** (BMI, calories, weight goals, explanations).
        - 'nutrition_request': SPECIFIC food requests ("Breakfast ideas", "high protein meals").
        - 'nutrition_options': VAGUE food inquiries ("what should I eat?", "diet plan").
        - 'fitness_request': Workout requests ("chest exercises", "cardio routine").
        - 'fitness_variation': User wants a DIFFERENT exercise ("give me another", "something else").
        - 'nutrition_variation': User wants DIFFERENT food ("show me other options").
        - 'explain_exercise': User asks for instructions ("how to do X").
        - 'workout_table': User wants a WEEKLY WORKOUT TABLE/TIMETABLE/SCHEDULE. Keywords: "timetable", "schedule", "weekly plan", "5 days workout".
        - 'log_weight': User wants to LOG their weight. Keywords: "I weigh", "log weight", "my weight is", "update weight", "kg today".
        - 'log_nutrition': User wants to LOG food/calories/macros consumed. Keywords: "I ate", "log calories", "had X protein", "consumed", "intake".
        - 'log_workout': User wants to LOG a completed workout. Keywords: "finished workout", "completed", "log workout", "did my", "just did".
        - 'view_progress': User wants to VIEW their progress history. Keywords: "show progress", "my weight history", "calories today", "workout history", "how much", "track".
        - 'coach_challenge': User avoids or complains about critical, high-impact exercises/foods.
        - 'out_of_scope': NON-FITNESS topics OR GIBBERISH.

        ### HEALTH QUESTION EXAMPLES (These are general_chat, NOT pathway_generation!)
        - "What is my BMI?" → {"intent": "general_chat", "entities": {}}
        - "What weight should I target for normal BMI?" → {"intent": "general_chat", "entities": {}}
        - "How many calories should I eat?" → {"intent": "general_chat", "entities": {}}
        - "I want to ask about my BMI if I want to target normal" → {"intent": "general_chat", "entities": {}}
        - "What are macros?" → {"intent": "general_chat", "entities": {}}
        - "How do I lose weight?" → {"intent": "general_chat", "entities": {}}
        
        ### WORKOUT TABLE EXAMPLES (These ARE workout_table - weekly schedules)
        - "Make me a weekly workout table" → {"intent": "workout_table", "entities": {"workout_days": 5, "rest_days": 2}}
        - "5 days workout 2 days rest timetable" → {"intent": "workout_table", "entities": {"workout_days": 5, "rest_days": 2}}
        - "Can you make a full timetable for me" → {"intent": "workout_table", "entities": {}}
        - "Create my workout schedule" → {"intent": "workout_table", "entities": {}}
        - "Show me a weekly routine" → {"intent": "workout_table", "entities": {}}

        ### CRITICAL EXAMPLES (Preference vs Request)
        - "I like chicken" → {"intent": "add_preference", "entities": {"preferences": ["chicken"]}}
        - "I love running" → {"intent": "add_preference", "entities": {"preferences": ["running"]}}
        - "I prefer vegan food" → {"intent": "add_preference", "entities": {"preferences": ["vegan food"]}}
        - "I like to use dumbbell" → {"intent": "add_preference", "entities": {"preferences": ["dumbbell"]}}
        - "I like to use dumbbell for workout" → {"intent": "add_preference", "entities": {"preferences": ["dumbbell"]}}
        - "I like using resistance bands" → {"intent": "add_preference", "entities": {"preferences": ["resistance bands"]}}
        - "I like barbell exercises" → {"intent": "add_preference", "entities": {"preferences": ["barbell"]}}
        - "I prefer bodyweight exercises" → {"intent": "add_preference", "entities": {"preferences": ["bodyweight"]}}
        - "I enjoy kettlebell workouts" → {"intent": "add_preference", "entities": {"preferences": ["kettlebell"]}}
        
        ### DISLIKE EXAMPLES (These should ALL be add_dislike, NOT fitness_request!)
        - "I don't like burpees" → {"intent": "add_dislike", "entities": {"dislikes": ["burpees"]}}
        - "I hate fish" → {"intent": "add_dislike", "entities": {"dislikes": ["fish"]}}
        - "I hate using kettlebell" → {"intent": "add_dislike", "entities": {"dislikes": ["kettlebell"]}}
        - "I don't like to use kettlebell" → {"intent": "add_dislike", "entities": {"dislikes": ["kettlebell"]}}
        - "I hate kettlebell" → {"intent": "add_dislike", "entities": {"dislikes": ["kettlebell"]}}
        - "I don't like machines" → {"intent": "add_dislike", "entities": {"dislikes": ["machines"]}}
        - "I hate cardio" → {"intent": "add_dislike", "entities": {"dislikes": ["cardio"]}}
        - "I don't like eating fish" → {"intent": "add_dislike", "entities": {"dislikes": ["fish"]}}
        - "I hate to eat fish" → {"intent": "add_dislike", "entities": {"dislikes": ["fish"]}}
        - "Not a fan of cardio" → {"intent": "add_dislike", "entities": {"dislikes": ["cardio"]}}
        - "Actually, I prefer yoga" → {"intent": "add_preference", "entities": {"preferences": ["yoga"]}}
        
        ### PURE PREFERENCE/DISLIKE COMBINATIONS (NO explicit request = add_preference or add_dislike!)
        - "I don't like kettlebell and hate fish" → {"intent": "add_dislike", "entities": {"dislikes": ["kettlebell", "fish"]}}
        - "I don't like to use kettlebell and hate to eat fish" → {"intent": "add_dislike", "entities": {"dislikes": ["kettlebell", "fish"]}}
        - "I like dumbbell and hate kettlebell" → {"intent": "add_preference", "entities": {"preferences": ["dumbbell"], "dislikes": ["kettlebell"]}}
        - "I prefer chicken but hate fish" → {"intent": "add_preference", "entities": {"preferences": ["chicken"], "dislikes": ["fish"]}}
        
        ### REQUEST EXAMPLES (These are NOT preferences - they ask for something specific)
        - "Give me chest exercises" → {"intent": "fitness_request", "entities": {"target": "Chest"}}
        - "Suggest high protein meals" → {"intent": "nutrition_request", "entities": {"target": "High Protein"}}
        - "I want a workout for legs" → {"intent": "fitness_request", "entities": {"target": "Legs"}}
        - "Show me breakfast ideas" → {"intent": "nutrition_request", "entities": {"target": "Breakfast"}}
        - "Something else please" → {"intent": "fitness_variation" or "nutrition_variation"}

        ### COMPOUND EXAMPLES (CRITICAL - Extract ALL preferences/dislikes even in requests!)
        - "I like chicken, give me recipes" → {"intent": "nutrition_request", "entities": {"target": "chicken", "preferences": ["chicken"]}}
        - "I like kettlebell and chicken" → {"intent": "add_preference", "entities": {"preferences": ["kettlebell", "chicken"]}}
        - "I like kettlebell but hate barbell, suggest abs workout" → {"intent": "fitness_request", "entities": {"target": "Abs", "preferences": ["kettlebell"], "dislikes": ["barbell"]}}
        - "I prefer dumbbells but don't like machines. Give me chest exercises" → {"intent": "fitness_request", "entities": {"target": "Chest", "preferences": ["dumbbells"], "dislikes": ["machines"]}}
        - "I hate cardio but love strength training, show me workouts" → {"intent": "fitness_request", "entities": {"target": "General", "preferences": ["strength training"], "dislikes": ["cardio"]}}
        - "No fish please, suggest me high protein dinner" → {"intent": "nutrition_request", "entities": {"target": "High Protein Dinner", "dislikes": ["fish"]}}
        - "I avoid dairy, give me breakfast ideas" → {"intent": "nutrition_request", "entities": {"target": "Breakfast", "dislikes": ["dairy"]}}

        ### PROGRESS TRACKING EXAMPLES (NEW!)
        - "I weigh 75kg today" → {"intent": "log_weight", "entities": {"weight": 75}}
        - "Log my weight: 80" → {"intent": "log_weight", "entities": {"weight": 80}}
        - "My weight is 68.5 kg" → {"intent": "log_weight", "entities": {"weight": 68.5}}
        - "Right now my weight is 70kg and what is my bmi?" → {"intent": "log_weight", "entities": {"weight": 70, "ask_bmi": true}}
        - "My weight is 65kg, calculate my bmi" → {"intent": "log_weight", "entities": {"weight": 65, "ask_bmi": true}}
        - "I'm 80kg now, what's my BMI?" → {"intent": "log_weight", "entities": {"weight": 80, "ask_bmi": true}}
        - "Update my weight to 72kg and show my BMI" → {"intent": "log_weight", "entities": {"weight": 72, "ask_bmi": true}}
        - "I ate 500 calories" → {"intent": "log_nutrition", "entities": {"calories": 500}}
        - "Log 50g protein" → {"intent": "log_nutrition", "entities": {"protein": 50}}
        - "Had 300 calories and 30g protein" → {"intent": "log_nutrition", "entities": {"calories": 300, "protein": 30}}
        - "I consumed 40g carbs" → {"intent": "log_nutrition", "entities": {"carbs": 40}}
        - "I finished my Chest workout" → {"intent": "log_workout", "entities": {"workout_name": "Chest"}}
        - "Just completed leg day" → {"intent": "log_workout", "entities": {"workout_name": "Leg"}}
        - "Log my back workout" → {"intent": "log_workout", "entities": {"workout_name": "Back"}}
        - "Show my weight progress" → {"intent": "view_progress", "entities": {"progress_type": "weight"}}
        - "How many calories have I eaten today?" → {"intent": "view_progress", "entities": {"progress_type": "nutrition"}}
        - "Show my workout history" → {"intent": "view_progress", "entities": {"progress_type": "workout"}}
        - "What's my calorie intake today?" → {"intent": "view_progress", "entities": {"progress_type": "nutrition"}}
        - "Track my progress" → {"intent": "view_progress", "entities": {"progress_type": "all"}}

        ### OUTPUT FORMAT (JSON ONLY)
        {"intent": "string", "entities": {"target": "string or null", "preferences": [], "dislikes": [], "category": "string or null", "weight": "number or null", "calories": "number or null", "protein": "number or null", "carbs": "number or null", "fat": "number or null", "workout_name": "string or null", "progress_type": "weight|nutrition|workout|all or null"}}
        """

        try:
            # Context window management
            context_str = json.dumps(chat_history[-3:]) if chat_history else "[]"

            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {context_str}\nUser Message: {message}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            result = json.loads(response.choices[0].message.content)

            # Normalization logic
            entities = result.get('entities', {})
            if isinstance(entities, str):
                result['entities'] = {'target': entities}

            # Fallback intent
            if not result.get('intent'):
                result['intent'] = 'general_chat'

            return result

        except Exception as e:
            print(f"NLU Error: {e}")
            return {"intent": "general_chat", "entities": {}}

    def _get_coach_intervention(self, message, profile):
        """Generates an 'Empathetic Performance Coach' persona response to challenge the user."""
        name = profile.get('name', 'Friend')
        goal = profile.get('goal', 'Maintenance')
        
        # Hardcoded Gold Standards for the persona to reference
        gold_standards = {
            'Weight Loss': ['HIIT', 'Burpees', 'Caloric Deficit', 'Fiber'],
            'Muscle Gain': ['Squats', 'Deadlifts', 'Bench Press', 'High Protein']
        }
        
        relevant_standards = []
        for k, v in gold_standards.items():
            if k in goal: relevant_standards.extend(v)

        system_prompt = f"""
        You are Atlas, an Empathetic Performance Coach.
        Your job is to be the user's friendly partner in success.
        
        ### KEY PERSONA TRAITS:
        - **Tone:** Mature, friendly, warm, yet disciplined. Use "We" language (e.g., "Let's reach our goal", "We can handle this").
        - **Philosophy:** Trust is built on understanding, but Progress is built on Truth.
        - **Strategy:** Validate -> Challenge -> Support.

        ### INTERVENTION STRUCTURE:
        1. **Validate:** Acknowledge their feeling (e.g., "I know squats are brutal," "It's normal to feel tired.").
        2. **The Truth (Pivot):** Gently explain why avoiding this hurts **OUR** goal (e.g., "But skipping leg day limits our total metabolism.").
        3. **Micro-Challenge:** Offer a compromise (e.g., "Let's just do 2 sets today?" or "What if we swap it for Leg Press just for today?").
        4. **Closing:** A warm confident nudge (e.g., "I know you've got this.").

        User Goal: {goal}
        Relevant Gold Standards: {', '.join(relevant_standards)}
        
        **OUTPUT FORMAT:** HTML ONLY. Use <b>bold</b> and <br> for structure. NO markdown blocks.
        """

        try:
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.8
            )
            return response.choices[0].message.content
        except:
            return f"I hear you, {name}. It's tough, but remember we're doing this for {goal}. Let's try to stick to the plan."

    def generate_response(self, profile, message, intent):
        """
        Generates a natural language response based on the intent.
        Enforces modern, structured, and profile-aware formatting.
        """
        name = profile.get('name', 'Friend')
        goal = profile.get('goal', 'better health')
        gender = profile.get('gender', 'Unknown')
        level = profile.get('fitness_level', 'Beginner')
        age = profile.get('age', 'Unknown')
        weight = profile.get('weight', 'Unknown')
        height = profile.get('height', 'Unknown')
        bmi = profile.get('bmi', 'Unknown')
        condition = profile.get('medical_conditions', 'None')

        # --- 1. HARD STOP FOR OUT OF SCOPE / GIBBERISH ---
        if intent == 'out_of_scope':
            return (
                f"I'm tuned to focus solely on your fitness and nutrition goals, {name}.<br><br>"
                "Let's get back to your training or diet plan! I can help you with workouts, "
                "healthy recipes, or recovery tips. <b>What would you like to do?</b>"
            )

        # --- 2. PREFERENCE CONFIRMATION ---
        if intent in ['add_preference', 'add_dislike']:
            return f"Got it, {name}. I've updated your preferences. I'll keep them in mind! What would you like to explore now?"

        if intent == 'clear_preferences':
            return f"No problem, {name}. I've cleared all your likes and dislikes. We're starting clean!"

        # Construct full context string safely
        user_context = f"""
        - Name: {name}
        - Primary Goal: {goal}
        - Gender: {gender}
        - Fitness Level: {level}
        - Age: {age}
        - Weight: {weight} kg
        - Height: {height} cm
        - BMI: {bmi}
        - Medical Conditions: {condition}
        """

        # --- SPECIAL HANDLER: NUTRITION OPTIONS (CLARIFICATION) ---
        if intent == 'nutrition_options':
            options = ["Breakfast", "Lunch", "Dinner", "Snack"]
            if 'Loss' in goal:
                options = ["Breakfast", "Lunch", "Dinner", "Low Calorie"]
                intro = f"I'd love to help with your nutrition, {name}! Since your goal is <b>Weight Loss</b>, I can find meals that fit your calorie targets.<br><br><b>Which meal specifically do you need ideas for?</b>"
            else:
                intro = f"I can certainly help with meal ideas, {name}! To give you the best recommendation for your goal, I need a little more detail.<br><br><b>Which meal time are you looking for?</b>"

            html = '<div class="flex flex-wrap gap-2 mt-3">'
            for opt in options:
                html += f"""<button onclick="sendQuick('{opt} ideas')" class="px-4 py-2 bg-brand-50 text-brand-600 rounded-full text-sm font-bold border border-brand-100 hover:bg-brand-600 hover:text-white transition-colors shadow-sm">{opt}</button>"""
            html += '</div>'
            return f"{intro}{html}"

        # --- LOGGING CONFIRMATION ---
        if intent in ['log_weight', 'log_nutrition', 'log_workout', 'view_progress']:
            return self._format_log_confirmation(intent, entities)

        # --- COACH CHALLENGE INTERVENTION ---
        if intent == 'coach_challenge':
            return self._get_coach_intervention(message, profile)

        # --- GENERAL CHAT & EXPLANATIONS (Modern Chatbot Style) ---
        system_prompt = f"""
        You are Atlas, an Empathetic Performance Coach.
        
        **USER PROFILE (USE THIS DATA FOR ALL CALCULATIONS!):**
        {user_context}
        
        **CRITICAL FORMATTING RULES:**
        1. **Use HTML tags for formatting** - Use <b>bold</b>, <br> for new lines.
        2. **Bullet lists:** Use <ul><li>item</li></ul> format.
        3. **KEEP RESPONSES COMPACT** - No excessive blank lines or spacing.
        4. **MAX LENGTH: 150-200 words** for explanations. Be concise!
        
        **CONTENT INSTRUCTIONS:**
        1. **Use Profile Data:** If user asks about BMI, weight targets, or calories, CALCULATE using the EXACT numbers from USER PROFILE above.
        2. **BMI Formula:** BMI = weight(kg) / (height(m))^2. Use the user's ACTUAL weight and height.
        3. **Start with a direct answer** - don't ramble.
        4. **Be BRIEF and actionable** - users want quick tips, not essays.
        5. **Tone:** Professional yet encouraging. Use "We" language.
        
        **FOR EXERCISE EXPLANATIONS:**
        - Use a single <b>header</b>, then 3-4 key bullet points only
        - Focus on: Setup, Key cues, Common mistake to avoid
        - Skip lengthy introductions - get straight to the form tips
        - If user asks for YouTube link, include: <br><br><a href="https://www.youtube.com/results?search_query=[EXERCISE NAME]+tutorial" target="_blank" class="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold transition-colors"><i class="fab fa-youtube"></i> Watch Tutorial</a>
        """


        try:
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content
            if not content:
                return "I'm here listening! How can I help you with your fitness journey today?"
            return content

        except Exception:
            return "I'm having a little trouble thinking right now. Could you ask that again?"

    def generate_recipe(self, food_name, profile):
        """
        Generates a formatted recipe card.
        """
        diet = "general"
        if 'Loss' in profile.get('goal', ''): diet = "low calorie, high volume"
        if 'Muscle' in profile.get('goal', ''): diet = "high protein"

        system_prompt = f"""
        You are a Michelin-star fitness chef.
        Task: Create a healthy, delicious recipe for: "{food_name}".
        Context: The user is on a **{diet}** diet.

        **OUTPUT FORMAT (HTML ONLY):**
        Return the raw HTML inside a `<div>`. Do not use markdown blocks.

        Structure & Design (Use Tailwind Classes for light/dark mode):

        1. **Recipe Header:**
           - Use a `<div>` with `p-6 bg-slate-50 dark:bg-slate-900 border-b border-slate-100 dark:border-slate-700`.
           - Title `<h3>` with `text-2xl font-black text-slate-800 dark:text-white mb-2 flex items-center gap-2`. Start with a relevant emoji.
           - Description `<p>` with `text-sm text-slate-500 dark:text-slate-400 italic`.

        2. **Ingredients Section:**
           - Use a `<div>` with `p-6 bg-white dark:bg-slate-800`.
           - Header `<h4>` with `font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider text-xs mb-4 flex items-center gap-2`. Use `<i class="fas fa-shopping-basket text-brand-500"></i>`.
           - List `<ul>` with `space-y-2`.
           - Items `<li>` with `flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300`. Use `<span class="text-brand-500 font-bold">•</span>` as bullet.

        3. **Instructions Section:**
           - Use a `<div>` with `p-6 pt-0 bg-white dark:bg-slate-800`.
           - Header `<h4>` with `font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider text-xs mb-4 flex items-center gap-2`. Use `<i class="fas fa-list-ol text-brand-500"></i>`.
           - List `<ol>` with `space-y-4`.
           - Items `<li>` with `flex gap-3 text-sm text-slate-600 dark:text-slate-300`. Use `<span class="w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400 text-xs font-bold flex items-center justify-center shrink-0">1</span>` for numbered circles.

        4. **Chef's Tip (at the end):**
           - Use a `<div>` with `mx-6 mb-6 p-4 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 rounded-xl text-sm border border-emerald-100 dark:border-emerald-800/30 flex gap-3 items-start`.
           - Icon: `<i class="fas fa-lightbulb text-emerald-500 mt-0.5"></i>`.
           - Content: `<span><b class="text-emerald-700 dark:text-emerald-300">Chef's Tip:</b> ...</span>`.

        IMPORTANT: Output ONLY the HTML. No markdown, no explanation.
        """

        try:
            response = self.client.chat.completions.create(
                model=Config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate recipe for: {food_name}"}
                ],
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception:
            return "<div class='text-red-500 font-bold p-6 text-center'>The chef is currently busy. Please try again in a moment!</div>"
