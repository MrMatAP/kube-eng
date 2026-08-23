from typing import Annotated

import pydantic


class InfraResult(pydantic.BaseModel):
    changed: Annotated[bool, pydantic.Field(default=False)]
    msg: Annotated[str, pydantic.Field(default='OK')]

    def ansible_result(self) -> dict:
        return self.model_dump(mode='python')

class InfraException(Exception):

    def __init__(self, code: int = 500, msg: str = 'Unknown'):
        self._code = code
        self._msg = msg

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code={self.code}, msg={self.msg})'

    def __str__(self) -> str:
        return f'[{self.code}] {self.msg}'

    def ansible_result(self) -> dict:
        return {'msg': self.msg}