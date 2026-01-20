from aiogram.fsm.state import State, StatesGroup

class Onboarding(StatesGroup):
    choosing_languages = State()
    choosing_levels = State()
