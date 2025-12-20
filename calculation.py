def calc_calorie(weight: float, height: float, age: float, gender: str, activity_level: float) -> float:
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    tdee = bmr * activity_level
    
    return round(tdee)


def calc_calorie_with_goal(base_calories: float, goal_type: str) -> float:
    if goal_type == 'lose':
        return round(base_calories * 0.9)
    elif goal_type == 'gain':
        return round(base_calories * 1.1)
    else:
        return round(base_calories)


def calc_water(weight: float, activity_level: float) -> float:
    base_water = weight * 30

    activity_bonus = (activity_level - 1.2) / (1.9 - 1.2) * 500
    
    total_water = base_water + activity_bonus
    
    return round(total_water)


