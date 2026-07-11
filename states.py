from aiogram.fsm.state import State, StatesGroup


class BuyFlow(StatesGroup):
    category = State()
    model = State()


class SparePartsFlow(StatesGroup):
    transport_type = State()
    brand = State()
    model = State()
    part_category = State()


class RepairFlow(StatesGroup):
    question = State()


class HelpFlow(StatesGroup):
    question = State()


class ReviewWriteFlow(StatesGroup):
    transport = State()
    rating = State()
    text = State()


class AdminPriceFlow(StatesGroup):
    choose_model = State()
    enter_price = State()


class AdminAddModelFlow(StatesGroup):
    category = State()
    name = State()
    power = State()
    range_ = State()
    weight = State()
    price = State()


class AdminDeleteModelFlow(StatesGroup):
    choose_model = State()


class AdminAddPersonFlow(StatesGroup):
    name = State()
    description = State()
    link = State()


class AdminBroadcastFlow(StatesGroup):
    text = State()
