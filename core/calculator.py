def calculate_bmi(weight, height):
    """Calculates BMI given weight (kg) and height (cm)."""
    if not weight or not height:
        return None
    try:
        h_m = height / 100
        return round(weight / (h_m ** 2), 1)
    except ZeroDivisionError:
        return None


def calculate_target_calories(weight, height, age, gender, goal):
    """
    Calculates daily target calories using Mifflin-St Jeor equation.
    """
    if not all([weight, height, age, gender]):
        return None

    # Mifflin-St Jeor Formula
    bmr = (10 * weight) + (6.25 * height) - (5 * age)
    bmr += 5 if gender == 'Male' else -161

    # Standard Activity Multiplier (Sedentary/Light assumed for baseline)
    tdee = bmr * 1.2

    # Goal Adjustment
    if 'Loss' in goal or 'Cut' in goal:
        target = tdee - 500
    elif 'Gain' in goal or 'Muscle' in goal:
        target = tdee + 300
    else:
        target = tdee

    return int(target)