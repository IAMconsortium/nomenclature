import pydantic


class TestModel(pydantic.BaseModel):
    some_attribute: str = pydantic.Field(alias="some-attribute")

    class Config:
        allow_population_by_field_name = True


tm1 = TestModel(some_attribute="test1")
print(tm1)

tm2 = TestModel(**{"some-attribute": "test2"})
print(tm2)
