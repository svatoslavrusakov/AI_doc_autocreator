from dataclasses import dataclass

@dataclass
class Bank:
    name: str             # наименование банка
    BIC: str              # БИК
    current_account: str  # расчётный счёт
    corporate_account: str # корреспондентский счёт

@dataclass
class Customer:
    name: str             # полное название юр. лица
    INN: str              # ИНН
    OGRN: str             # ОГРН или ОГРНИП
    address: str          # юридический адрес
    signatory: str        # подписант (например, Иванов А.Е.)
    bank: Bank            # банковские реквизиты

@dataclass
class Job:
    task: str             # выполненная задача
    price: int            # цена за задачу
