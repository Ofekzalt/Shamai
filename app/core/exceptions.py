class ShamaiError(Exception):
    pass


class AddressNotGeocodedError(ShamaiError):
    def __init__(self, street: str, house_number: str) -> None:
        super().__init__(
            "Shamai covers Tel Aviv–Yafo municipal addresses only; "
            f"no match in the municipal geocoder for {street!r} {house_number!r}."
        )
        self.street = street
        self.house_number = house_number
