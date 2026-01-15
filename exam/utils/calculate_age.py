import datetime

def calculate_age(birthdate):
    today = datetime.datetime.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age