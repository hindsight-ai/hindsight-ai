from core.workers import async_bulk_operations as shim
import core.async_bulk_operations as impl


def test_async_bulk_operations_shim_reexports():
    assert shim.execute_bulk_operation_async is impl.execute_bulk_operation_async
    assert shim.get_bulk_operation_status is impl.get_bulk_operation_status
    assert shim.cancel_bulk_operation is impl.cancel_bulk_operation
    assert shim.get_running_bulk_operations_count is impl.get_running_bulk_operations_count

