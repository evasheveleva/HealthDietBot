def calc_calorie(weight: float, height: float, age: float, gender: str, activity_level: float) -> float:
    if gender.lower() == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:  # female
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    tdee = bmr * activity_level
    
    return round(tdee)


def calc_water(weight: float, activity_level: float) -> float:
    base_water = weight * 30

    activity_bonus = (activity_level - 1.2) / (1.9 - 1.2) * 500
    
    total_water = base_water + activity_bonus
    
    return round(total_water)

