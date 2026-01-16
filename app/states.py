from aiogram.fsm.state import State, StatesGroup

class Onboarding(StatesGroup):
    choosing_es = State()
    choosing_it = State()
