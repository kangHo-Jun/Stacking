class DispatchError(Exception):
    """Base class for all dispatch and stacking errors."""
    pass

class DataInvalidError(DispatchError):
    """Raised when master data (material/vehicle) is missing or corrupted."""
    pass

class LoadingFailedError(DispatchError):
    """Raised when geo-packing or stability calculation fails due to invalid logic or data."""
    pass

class NoFeasibleVehicleError(DispatchError):
    """Raised when no suitable vehicle (stable or otherwise) can be found for the order."""
    pass
