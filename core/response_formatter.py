def format_exercise_card(recs, intent, target):
    """
    Generates MODERN HTML for fitness recommendations with Numbering.
    """
    prefix = "Here are some <b>variations</b>" if intent == 'fitness_variation' else f"Here are some <b>{target}</b> exercises"
    html = f"<p class='mb-6 text-lg text-slate-700 dark:text-slate-300'>{prefix} for you:</p>"

    for i, r in enumerate(recs, 1):
        yt_query = f"{r['Title']} proper form exercise".replace(" ", "+")
        protocol = r.get('protocol', '3 Sets • 10 Reps')
        num_str = f"{i:02d}"

        html += f"""
        <div class="exercise-card group relative bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-300 mb-6 overflow-visible">
            <div class="absolute -left-3 -top-3 w-8 h-8 bg-brand-600 text-white rounded-full flex items-center justify-center font-black text-xs shadow-lg z-10 border-2 border-white dark:border-slate-800">
                {num_str}
            </div>

            <div class="p-5">
                <div class="flex justify-between items-start mb-3 pl-2">
                    <div>
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white leading-tight">{r['Title']}</h3>
                        <div class="flex items-center gap-2 mt-1">
                             <span class="text-[10px] font-bold uppercase tracking-wider text-brand-600 bg-brand-50 dark:bg-brand-900/30 px-2 py-0.5 rounded-full">{r['Level']}</span>
                             <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">{r['Type']}</span>
                        </div>
                    </div>
                </div>

                <div class="bg-slate-50 dark:bg-slate-700/30 rounded-xl p-3 mb-4 border border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center text-brand-500 shadow-sm">
                        <i class="fas fa-clipboard-list"></i>
                    </div>
                    <div>
                        <div class="text-[10px] uppercase text-slate-400 font-bold tracking-wider">Protocol</div>
                        <div class="font-bold text-slate-700 dark:text-slate-200 text-sm">{protocol}</div>
                    </div>
                </div>

                <details class="group/desc mb-4">
                    <summary class="flex items-center gap-2 cursor-pointer text-xs font-bold text-slate-500 hover:text-brand-600 transition-colors select-none">
                        <i class="fas fa-chevron-right text-[10px] transition-transform group-open/desc:rotate-90"></i>
                        <span>How to perform</span>
                    </summary>
                    <div class="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed pl-4 border-l-2 border-slate-200 dark:border-slate-700">
                        {r.get('Desc', 'No description available.')}
                    </div>
                </details>

                <div class="flex gap-2 mt-4">
                    <a href="https://www.youtube.com/results?search_query={yt_query}" target="_blank" class="flex-1 text-center py-2.5 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-bold hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors">
                        <i class="fab fa-youtube text-red-500 mr-1"></i> Watch
                    </a>
                    <button onclick="sendQuick('Explain form for {r['Title']}')" class="flex-[2] text-center py-2.5 bg-brand-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-500/20 hover:bg-brand-700 hover:shadow-brand-500/40 transition-all transform hover:-translate-y-0.5">
                        Explain Details
                    </button>
                </div>
            </div>
        </div>
        """
    return html


def format_nutrition_card(recs, intent, target):
    """
    Generates ENHANCED & STYLISH HTML for nutrition recommendations.
    Aligned with Fitness Card design for consistency.
    """
    prefix = "Here are other <b>options</b>" if intent == 'nutrition_variation' else f"Here are some <b>{target}</b> ideas"
    html = f"<p class='mb-6 text-lg text-slate-700 dark:text-slate-300'>{prefix} for you:</p>"

    for i, r in enumerate(recs, 1):
        num_str = f"{i:02d}"

        # Dynamic Icon Logic
        cat = r.get('Category', 'Meal')
        icon = "fa-utensils"

        if 'Breakfast' in r.get('Meal_Type', ''):
            icon = "fa-coffee"
        elif 'Salad' in cat or 'Vegetable' in cat:
            icon = "fa-leaf"
        elif 'Smoothie' in cat or 'Drink' in cat:
            icon = "fa-blender"
        elif 'Meat' in cat or 'Chicken' in cat:
            icon = "fa-drumstick-bite"
        elif 'Seafood' in cat:
            icon = "fa-fish"

        # Ensure numeric display
        cals = int(r.get('Calories', 0))
        pro = int(r.get('Protein', 0))
        carb = int(r.get('Carbs', 0))
        fat = int(r.get('Fat', 0))

        html += f"""
        <div class="nutrition-card group relative bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-300 mb-6 overflow-visible">
            <div class="absolute -left-3 -top-3 w-8 h-8 bg-brand-600 text-white rounded-full flex items-center justify-center font-black text-xs shadow-lg z-10 border-2 border-white dark:border-slate-800">
                {num_str}
            </div>

            <div class="p-5">
                <!-- Header Section -->
                <div class="flex justify-between items-start mb-4 pl-2">
                    <div>
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white leading-tight mb-1">{r['Name']}</h3>
                         <span class="text-[10px] font-bold uppercase tracking-wider text-brand-600 bg-brand-50 dark:bg-brand-900/30 px-2 py-0.5 rounded-full">{r.get('Category', 'Meal')}</span>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-brand-600 dark:text-brand-400 leading-none">{cals}</div>
                        <div class="text-[9px] font-bold uppercase text-slate-400">kcal</div>
                    </div>
                </div>

                <!-- Highlight Box (Similar to Protocol Box) -->
                <div class="bg-slate-50 dark:bg-slate-700/30 rounded-xl p-3 mb-4 border border-slate-100 dark:border-slate-700/50 flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center text-brand-500 shadow-sm shrink-0">
                        <i class="fas {icon}"></i>
                    </div>
                    <div class="flex-1 grid grid-cols-3 gap-2 text-center">
                        <div>
                            <div class="text-[9px] uppercase text-slate-400 font-bold tracking-wider">Pro</div>
                            <div class="font-bold text-emerald-600 text-sm">{pro}g</div>
                        </div>
                        <div>
                            <div class="text-[9px] uppercase text-slate-400 font-bold tracking-wider">Carb</div>
                            <div class="font-bold text-amber-600 text-sm">{carb}g</div>
                        </div>
                        <div>
                            <div class="text-[9px] uppercase text-slate-400 font-bold tracking-wider">Fat</div>
                            <div class="font-bold text-rose-600 text-sm">{fat}g</div>
                        </div>
                    </div>
                </div>

                <!-- Action Button -->
                <div class="flex gap-2 mt-4">
                    <button onclick="getRecipe('{r['Name']}')" class="w-full text-center py-2.5 bg-brand-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-500/20 hover:bg-brand-700 hover:shadow-brand-500/40 transition-all transform hover:-translate-y-0.5 flex items-center justify-center gap-2">
                        <i class="fas fa-magic"></i> Generate AI Recipe
                    </button>
                </div>
            </div>
         </div>
         """
    return html