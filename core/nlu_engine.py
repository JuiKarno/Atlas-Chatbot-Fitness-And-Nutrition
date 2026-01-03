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
        
        2. **HEALTH QUESTIONS (Check SECOND - VERY IMPORTANT)**
           - Questions about BMI, weight, calories, macros, body fat, target weight → `general_chat`
           - "What is my BMI?", "What weight should I target?", "How many calories?" → `general_chat`
           - Questions asking for calculation, explanation, or advice → `general_chat`
        
        3. **REQUEST DETECTION (Check AFTER above)**
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
        - "I don't like burpees" → {"intent": "add_dislike", "entities": {"dislikes": ["burpees"]}}
        - "I hate fish" → {"intent": "add_dislike", "entities": {"dislikes": ["fish"]}}
        - "Not a fan of cardio" → {"intent": "add_dislike", "entities": {"dislikes": ["cardio"]}}
        - "Actually, I prefer yoga" → {"intent": "add_preference", "entities": {"preferences": ["yoga"]}}
        
        ### REQUEST EXAMPLES (These are NOT preferences)
        - "Give me chest exercises" → {"intent": "fitness_request", "entities": {"target": "Chest"}}
        - "Suggest high protein meals" → {"intent": "nutrition_request", "entities": {"target": "High Protein"}}
        - "I want a workout for legs" → {"intent": "fitness_request", "entities": {"target": "Legs"}}
        - "Show me breakfast ideas" → {"intent": "nutrition_request", "entities": {"target": "Breakfast"}}
        - "Something else please" → {"intent": "fitness_variation" or "nutrition_variation"}

        ### COMPOUND EXAMPLES
        - "I like chicken, give me recipes" → {"intent": "nutrition_request", "entities": {"target": "chicken", "preferences": ["chicken"]}}
        - "I like kettlebell and chicken" → {"intent": "add_preference", "entities": {"preferences": ["kettlebell", "chicken"]}}

        ### OUTPUT FORMAT (JSON ONLY)
        {"intent": "string", "entities": {"target": "string or null", "preferences": ["string", ...], "dislikes": ["string", ...], "category": "string or null"}}
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

        # --- GENERAL CHAT & EXPLANATIONS (Modern Chatbot Style) ---
        system_prompt = f"""
        You are Atlas, a highly intelligent and supportive AI Fitness Coach.

        **YOUR GOAL:** Provide clear, scientifically accurate, and personalized answers about fitness and health.

        **USER PROFILE (USE THIS DATA!):**
        {user_context}

        **CRITICAL FORMATTING RULES (YOU MUST FOLLOW THESE!):**
        1. **Use HTML tags for formatting** - This is displayed in a web chat, NOT markdown!
        2. **Line breaks:** Use `<br>` for new lines, NOT newline characters.
        3. **Bold text:** Use `<b>text</b>` for emphasis.
        4. **Bullet lists:** Use `<ul><li>item</li></ul>` format.
        5. **Numbered lists:** Use `<ol><li>item</li></ol>` format.
        6. **Paragraphs:** Keep to 2-3 sentences max. Add `<br><br>` between paragraphs.
        7. **Tables:** Use proper `<table>` HTML if showing data tables.
        
        **CONTENT INSTRUCTIONS:**
        1. **Use Profile Data:** If user asks about BMI, weight targets, or calories, USE the numbers from USER PROFILE. Calculate if needed.
        2. **Start with a direct answer** - don't ramble.
        3. **Explain the 'Why'** briefly before giving specific numbers.
        4. **Tone:** Professional yet encouraging.

        **EXAMPLE RESPONSE (User asks about BMI):**
        Based on your height of <b>175cm</b> and weight of <b>70kg</b>, your current BMI is <b>22.9</b>.<br><br>This places you in the <b>Normal Weight</b> category, which is great!<br><br>Here's a quick breakdown:<ul><li><b>Current BMI:</b> 22.9</li><li><b>Healthy Range:</b> 18.5 - 24.9</li><li><b>Target Weight:</b> 65-76 kg</li></ul>Would you like a workout plan to help build lean muscle?
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

        Structure & Design (Use Tailwind Classes):
        1. **Header:** - Use a `<div>` with `bg-gradient-to-r from-orange-100 to-amber-100 dark:from-slate-700 dark:to-slate-800 p-6 rounded-t-3xl border-b border-orange-200 dark:border-slate-600`.
           - Inside, put the Title `<h3>` with `text-2xl font-black text-slate-800 dark:text-white mb-2 flex items-center gap-2`. Use a relevant emoji.
           - Add the Description `<p>` with `text-sm text-slate-600 dark:text-slate-300 italic`.

        2. **Ingredients Section:**
           - Use a `<div>` with `p-6 bg-white dark:bg-slate-900`.
           - Header `<h4>` with `font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider text-xs mb-3 flex items-center gap-2`. Use icon `<i class="fas fa-shopping-basket"></i>` (FontAwesome).
           - List `<ul>` with `space-y-2`.
           - Items `<li>` with `flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 before:content-['•'] before:text-brand-500 before:font-bold`.

        3. **Instructions Section:**
           - Use a `<div>` with `p-6 pt-0 bg-white dark:bg-slate-900`.
           - Header `<h4>` with `font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider text-xs mb-3 flex items-center gap-2`. Use icon `<i class="fas fa-list-ol"></i>`.
           - List `<ol>` with `space-y-4`.
           - Items `<li>` with `flex gap-3 text-sm text-slate-600 dark:text-slate-300`. Use a span for the number (e.g., `<span class="font-bold text-brand-600">1.</span>`).

        4. **Chef's Tip:**
           - Use a `<div>` with `p-4 m-6 mt-0 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300 rounded-2xl text-sm border border-emerald-100 dark:border-emerald-800/30 flex gap-3 items-start`.
           - Icon `<i class="fas fa-lightbulb mt-1"></i>`.
           - Content `<span><b>Chef's Tip:</b> ... </span>`.

        Output ONLY the HTML.
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
            return "<div class='text-red-500 font-bold'>The chef is currently busy. Please try again in a moment!</div>"