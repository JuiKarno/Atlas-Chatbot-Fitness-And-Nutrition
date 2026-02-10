import json

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

        # Serialize item for JS
        item_json = json.dumps(r).replace('"', '&quot;')

        html += f"""
        <div class="exercise-card group relative bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 hover:shadow-md transition-all duration-300 mb-6 overflow-visible">
            <!-- Feedback Controls -->
            <div class="absolute right-3 top-3 flex gap-2 z-20">
                <button onclick='toggleFavorite(this, {item_json}, "exercise")' class="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-700/80 backdrop-blur-sm shadow-sm flex items-center justify-center text-slate-400 hover:text-amber-500 transition-colors">
                    <i class="fas fa-star text-xs"></i>
                </button>
                <button onclick='hideItem(this, {item_json}, "exercise")' class="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-700/80 backdrop-blur-sm shadow-sm flex items-center justify-center text-slate-400 hover:text-rose-500 transition-colors">
                    <i class="fas fa-times text-xs"></i>
                </button>
            </div>

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
                    <button onclick="sendQuick('How to do {r['Title']}')" class="flex-[2] text-center py-2.5 bg-brand-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-500/20 hover:bg-brand-700 hover:shadow-brand-500/40 transition-all transform hover:-translate-y-0.5">
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

        # Serialize item for JS
        item_json = json.dumps(r).replace('"', '&quot;')

        html += f"""
        <div class="nutrition-card group relative bg-white dark:bg-slate-800 rounded-2xl shadow-md dark:shadow-xl border border-slate-100 dark:border-slate-700 hover:shadow-lg transition-all duration-300 mb-6 overflow-visible">
            <!-- Number Badge -->
            <div class="absolute -left-2 -top-2 w-9 h-9 bg-brand-600 text-white rounded-xl flex items-center justify-center font-black text-sm shadow-lg z-10">
                {num_str}
            </div>
            
            <!-- Feedback Controls -->
            <div class="absolute right-3 top-3 flex gap-2 z-20">
                <button onclick='toggleFavorite(this, {item_json}, "nutrition")' class="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-amber-500 transition-colors">
                    <i class="fas fa-star text-xs"></i>
                </button>
                <button onclick='hideItem(this, {item_json}, "nutrition")' class="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-rose-500 transition-colors">
                    <i class="fas fa-times text-xs"></i>
                </button>
            </div>

            <div class="p-5 pt-4">
                <!-- Header with Icon -->
                <div class="flex items-start gap-3 mb-4 ml-5">
                    <div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center text-brand-600 dark:text-brand-400 shrink-0">
                        <i class="fas {icon} text-lg"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white leading-tight mb-1.5 truncate">{r['Name']}</h3>
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-white bg-brand-600 px-2 py-0.5 rounded">{r.get('Meal_Type', 'Meal')}</span>
                            <span class="text-slate-400 text-xs">•</span>
                            <span class="text-slate-500 dark:text-slate-400 text-xs font-medium">{r.get('Category', '')}</span>
                        </div>
                    </div>
                </div>

                <!-- Total Energy Section -->
                <div class="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 mb-4 border border-slate-100 dark:border-slate-700">
                    <div class="flex items-center justify-between">
                        <div>
                            <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Total Energy</div>
                            <div class="flex items-baseline gap-1">
                                <span class="text-3xl font-black text-slate-800 dark:text-white">{cals}</span>
                                <span class="text-sm font-medium text-slate-400">kcal</span>
                            </div>
                        </div>
                        <div class="w-12 h-12 rounded-full bg-brand-600 flex items-center justify-center shadow-lg">
                            <i class="fas fa-fire-alt text-white text-xl"></i>
                        </div>
                    </div>
                </div>

                <!-- Macro Progress Bars -->
                <div class="space-y-3 mb-5">
                    <!-- Protein -->
                    <div class="flex items-center gap-3">
                        <div class="w-16 text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Protein</div>
                        <div class="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div class="h-full bg-emerald-500 rounded-full" style="width: {min(100, pro * 2)}%"></div>
                        </div>
                        <div class="w-10 text-right text-sm font-bold text-emerald-600 dark:text-emerald-400">{pro}g</div>
                    </div>
                    <!-- Carbs -->
                    <div class="flex items-center gap-3">
                        <div class="w-16 text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Carbs</div>
                        <div class="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div class="h-full bg-amber-500 rounded-full" style="width: {min(100, carb)}%"></div>
                        </div>
                        <div class="w-10 text-right text-sm font-bold text-amber-600 dark:text-amber-400">{carb}g</div>
                    </div>
                    <!-- Fat -->
                    <div class="flex items-center gap-3">
                        <div class="w-16 text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Fat</div>
                        <div class="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                            <div class="h-full bg-rose-500 rounded-full" style="width: {min(100, fat * 2)}%"></div>
                        </div>
                        <div class="w-10 text-right text-sm font-bold text-rose-600 dark:text-rose-400">{fat}g</div>
                    </div>
                </div>

                <!-- Action Button -->
                <button onclick="getRecipe('{r['Name']}')" class="w-full py-3 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40 transition-all transform hover:-translate-y-0.5 flex items-center justify-center gap-2">
                    <i class="fas fa-wand-magic-sparkles"></i> Generate AI Recipe
                </button>
            </div>
        </div>
        """
    return html


# ============================================
# PROGRESS TRACKING FORMATTERS
# ============================================

def format_progress_report(logs, log_type):
    """
    Generates a Tailwind-styled HTML report for weight/nutrition logs.
    """
    if not logs:
        return "<div class='p-4 bg-slate-100 rounded-lg text-slate-500 text-center italic'>No logs found for this period.</div>"

    html = "<div class='space-y-3'>"
    
    if log_type == 'weight':
        # Calculate stats
        weights = [l['weight'] for l in logs]
        avg = sum(weights) / len(weights)
        change = weights[-1] - weights[0]
        trend_icon = "fa-arrow-down text-emerald-500" if change < 0 else "fa-arrow-up text-amber-500"
        
        html += f"""
        <div class="grid grid-cols-2 gap-3 mb-4">
            <div class="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-xl border border-blue-100 dark:border-blue-800">
                <div class="text-xs text-slate-500 uppercase font-bold tracking-wider">Average</div>
                <div class="text-2xl font-black text-slate-800 dark:text-slate-200">{avg:.1f} <span class="text-xs font-normal">kg</span></div>
            </div>
            <div class="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-100 dark:border-slate-700">
                <div class="text-xs text-slate-500 uppercase font-bold tracking-wider">Change (7d)</div>
                <div class="text-2xl font-black text-slate-800 dark:text-slate-200 flex items-center gap-2">
                    {abs(change):.1f} <i class="fas {trend_icon} text-sm"></i>
                </div>
            </div>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-slate-700">
        """
        for log in logs:
            html += f"""
            <div class="flex justify-between py-2 text-sm">
                <span class="text-slate-500">{log['date']}</span>
                <span class="font-bold text-slate-700 dark:text-slate-300">{log['weight']} kg</span>
            </div>
            """
            
    elif log_type == 'nutrition':
        # Simple list for now
        for log in logs:
             html += f"""
            <div class="flex justify-between py-2 text-sm border-b border-slate-100 dark:border-slate-700 last:border-0">
                <span class="text-slate-500">{log['date']}</span>
                <div class="text-right">
                    <div class="font-bold text-slate-700 dark:text-slate-300">{log.get('calories', 0)} kcal</div>
                    <div class="text-xs text-slate-400">{log.get('protein', 0)}g P • {log.get('carbs', 0)}g C</div>
                </div>
            </div>
            """
            
    html += "</div></div>"
    return html

def format_log_confirmation(log_type, data):
    """
    Formats a confirmation message after logging weight/nutrition/workout.
    """
    icon_map = {
        'weight': ('fa-weight', 'emerald'),
        'nutrition': ('fa-utensils', 'amber'),
        'workout': ('fa-dumbbell', 'blue')
    }
    icon, color = icon_map.get(log_type, ('fa-check', 'brand'))

    # Build content based on log type
    if log_type == 'weight':
        weight = data.get('weight', 0)
        bmi = data.get('bmi')
        bmi_text = f" (BMI: <b>{bmi}</b>)" if bmi else ""
        content = f"<b>{weight} kg</b>{bmi_text}"
        title = "Weight Logged!"
    elif log_type == 'nutrition':
        parts = []
        if data.get('calories'): parts.append(f"<b>{data['calories']}</b> kcal")
        if data.get('protein'): parts.append(f"<b>{data['protein']}g</b> protein")
        if data.get('carbs'): parts.append(f"<b>{data['carbs']}g</b> carbs")
        if data.get('fat'): parts.append(f"<b>{data['fat']}g</b> fat")
        content = " • ".join(parts) if parts else "Updated!"
        title = "Nutrition Logged!"
    elif log_type == 'workout':
        workout_name = data.get('workout_name', 'Workout')
        content = f"<b>{workout_name}</b> workout completed!"
        title = "Workout Logged!"
    else:
        content = "Logged successfully!"
        title = "Success!"
    
    return f"""
    <div class="bg-{color}-50 dark:bg-{color}-900/20 border border-{color}-200 dark:border-{color}-800 rounded-2xl p-5">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-full bg-{color}-100 dark:bg-{color}-800 text-{color}-600 dark:text-{color}-300 flex items-center justify-center text-xl">
                <i class="fas {icon}"></i>
            </div>
            <div>
                <h4 class="font-bold text-{color}-800 dark:text-{color}-200 text-lg">{title}</h4>
                <p class="text-sm text-{color}-700 dark:text-{color}-300">{content}</p>
            </div>
        </div>
    </div>
    """


def format_weight_report(logs, current_weight, current_bmi=None):
    """
    Formats a weight progress report with history and trend.
    """
    if not logs:
        return """
        <div class="bg-slate-50 dark:bg-slate-800 rounded-2xl p-6 text-center">
            <i class="fas fa-weight text-4xl text-slate-300 dark:text-slate-600 mb-3"></i>
            <p class="text-slate-500 dark:text-slate-400 font-medium">No weight history yet.</p>
            <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">Say "I weigh X kg" to start tracking!</p>
        </div>
        """

    # Calculate trend
    if len(logs) >= 2:
        first_weight = logs[0]['weight']
        last_weight = logs[-1]['weight']
        change = last_weight - first_weight
        trend_icon = "fa-arrow-down text-emerald-500" if change < 0 else "fa-arrow-up text-rose-500" if change > 0 else "fa-minus text-slate-400"
        trend_text = f"{abs(change):.1f} kg {'lost' if change < 0 else 'gained' if change > 0 else 'no change'}"
    else:
        trend_icon = "fa-minus text-slate-400"
        trend_text = "Not enough data for trend"

    # Build table rows
    rows = ""
    prev_weight = None
    for log in logs[-7:]:  # Last 7 entries
        weight = log['weight']
        date = log['date']
        if prev_weight:
            diff = weight - prev_weight
            diff_class = "text-emerald-500" if diff < 0 else "text-rose-500" if diff > 0 else "text-slate-400"
            diff_text = f"{diff:+.1f}"
        else:
            diff_class = "text-slate-400"
            diff_text = "-"
        prev_weight = weight

        rows += f"""
        <tr class="border-b border-slate-100 dark:border-slate-700">
            <td class="py-2 text-sm text-slate-600 dark:text-slate-300">{date}</td>
            <td class="py-2 text-sm font-bold text-slate-800 dark:text-white">{weight} kg</td>
            <td class="py-2 text-sm font-medium {diff_class}">{diff_text}</td>
        </tr>
        """

    bmi_display = f'<span class="text-sm text-slate-500">BMI: <b>{current_bmi}</b></span>' if current_bmi else ""

    return f"""
    <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-lg">
        <div class="bg-gradient-to-r from-emerald-500 to-teal-500 px-5 py-4">
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="text-xl font-black text-white"><i class="fas fa-weight mr-2"></i>Weight Progress</h3>
                    <p class="text-sm text-white/80 mt-1">Last 7 days</p>
                </div>
                <div class="text-right">
                    <div class="text-3xl font-black text-white">{current_weight} kg</div>
                    {bmi_display}
                </div>
            </div>
        </div>
        
        <div class="p-5">
            <div class="flex items-center gap-3 mb-4 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                <i class="fas {trend_icon} text-xl"></i>
                <span class="font-medium text-slate-700 dark:text-slate-300">{trend_text}</span>
            </div>
            
            <table class="w-full">
                <thead>
                    <tr class="text-xs text-slate-400 uppercase tracking-wider">
                        <th class="text-left pb-2">Date</th>
                        <th class="text-left pb-2">Weight</th>
                        <th class="text-left pb-2">Change</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </div>
    """


def format_nutrition_report(today_data, target_calories=2000):
    """
    Formats today's nutrition with progress bars.
    """
    calories = today_data.get('calories', 0)
    protein = today_data.get('protein', 0)
    carbs = today_data.get('carbs', 0)
    fat = today_data.get('fat', 0)
    date = today_data.get('date', 'Today')

    # Calculate percentages (with caps at 100%)
    cal_pct = min(100, int((calories / target_calories) * 100)) if target_calories else 0
    
    # Default daily targets (can be made dynamic later)
    protein_target = 150
    carbs_target = 250
    fat_target = 65
    
    pro_pct = min(100, int((protein / protein_target) * 100)) if protein_target else 0
    carb_pct = min(100, int((carbs / carbs_target) * 100)) if carbs_target else 0
    fat_pct = min(100, int((fat / fat_target) * 100)) if fat_target else 0

    return f"""
    <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-lg">
        <div class="bg-gradient-to-r from-amber-500 to-orange-500 px-5 py-4">
            <div class="flex justify-between items-center">
                <div>
                    <h3 class="text-xl font-black text-white"><i class="fas fa-utensils mr-2"></i>Today's Nutrition</h3>
                    <p class="text-sm text-white/80 mt-1">{date}</p>
                </div>
                <div class="text-right">
                    <div class="text-3xl font-black text-white">{calories}</div>
                    <div class="text-sm text-white/80">of {target_calories} kcal</div>
                </div>
            </div>
        </div>
        
        <div class="p-5 space-y-4">
            <!-- Calories Bar -->
            <div>
                <div class="flex justify-between mb-1">
                    <span class="text-sm font-bold text-slate-700 dark:text-slate-300">Calories</span>
                    <span class="text-sm font-medium text-slate-500">{calories} / {target_calories} kcal</span>
                </div>
                <div class="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-3">
                    <div class="bg-gradient-to-r from-amber-400 to-orange-500 h-3 rounded-full transition-all" style="width: {cal_pct}%"></div>
                </div>
            </div>
            
            <!-- Macros Grid -->
            <div class="grid grid-cols-3 gap-3 mt-4">
                <!-- Protein -->
                <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-3 text-center">
                    <div class="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-1">Protein</div>
                    <div class="text-xl font-black text-emerald-700 dark:text-emerald-400">{protein}g</div>
                    <div class="w-full bg-emerald-100 dark:bg-emerald-800 rounded-full h-1.5 mt-2">
                        <div class="bg-emerald-500 h-1.5 rounded-full" style="width: {pro_pct}%"></div>
                    </div>
                </div>
                
                <!-- Carbs -->
                <div class="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-3 text-center">
                    <div class="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">Carbs</div>
                    <div class="text-xl font-black text-amber-700 dark:text-amber-400">{carbs}g</div>
                    <div class="w-full bg-amber-100 dark:bg-amber-800 rounded-full h-1.5 mt-2">
                        <div class="bg-amber-500 h-1.5 rounded-full" style="width: {carb_pct}%"></div>
                    </div>
                </div>
                
                <!-- Fat -->
                <div class="bg-rose-50 dark:bg-rose-900/20 rounded-xl p-3 text-center">
                    <div class="text-xs font-bold text-rose-600 uppercase tracking-wider mb-1">Fat</div>
                    <div class="text-xl font-black text-rose-700 dark:text-rose-400">{fat}g</div>
                    <div class="w-full bg-rose-100 dark:bg-rose-800 rounded-full h-1.5 mt-2">
                        <div class="bg-rose-500 h-1.5 rounded-full" style="width: {fat_pct}%"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


def format_workout_history(logs):
    """
    Formats workout history as a list of cards.
    """
    if not logs:
        return """
        <div class="bg-slate-50 dark:bg-slate-800 rounded-2xl p-6 text-center">
            <i class="fas fa-dumbbell text-4xl text-slate-300 dark:text-slate-600 mb-3"></i>
            <p class="text-slate-500 dark:text-slate-400 font-medium">No workout history yet.</p>
            <p class="text-sm text-slate-400 dark:text-slate-500 mt-1">Say "I finished my chest workout" to start tracking!</p>
        </div>
        """

    cards = ""
    for i, log in enumerate(logs[-5:], 1):  # Last 5 workouts
        workout_name = log.get('workout_name', 'Workout')
        date = log.get('date', '')
        exercises = log.get('exercises', [])
        duration = log.get('duration')

        exercise_list = ""
        if exercises:
            for ex in exercises[:3]:  # Show max 3 exercises
                name = ex.get('name', 'Exercise')
                sets = ex.get('sets', '-')
                reps = ex.get('reps', '-')
                exercise_list += f'<span class="text-xs bg-slate-100 dark:bg-slate-700 px-2 py-1 rounded-full">{name}: {sets}x{reps}</span>'

        duration_text = f'<span class="text-xs text-slate-400"><i class="fas fa-clock mr-1"></i>{duration} min</span>' if duration else ""

        cards += f"""
        <div class="bg-white dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700 p-4 mb-3 hover:shadow-md transition-shadow">
            <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-sm">
                        {i:02d}
                    </div>
                    <div>
                        <h4 class="font-bold text-slate-800 dark:text-white">{workout_name}</h4>
                        <p class="text-xs text-slate-400">{date}</p>
                    </div>
                </div>
                {duration_text}
            </div>
            <div class="flex flex-wrap gap-1 mt-2">
                {exercise_list}
            </div>
        </div>
        """

    return f"""
    <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-lg">
        <div class="bg-gradient-to-r from-blue-500 to-indigo-500 px-5 py-4">
            <h3 class="text-xl font-black text-white"><i class="fas fa-history mr-2"></i>Workout History</h3>
            <p class="text-sm text-white/80 mt-1">Last {len(logs[-5:])} workouts</p>
        </div>
        <div class="p-4">
            {cards}
        </div>
    </div>
    """
