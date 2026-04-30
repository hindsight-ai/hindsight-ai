import notificationService from '../services/notificationService';
import type { INotificationService } from '../services/notificationService.types';
import { ApiError, AuthenticationError, AuthorizationError, NetworkError } from './errors';

export function showErrorToast(error: unknown, service: INotificationService = notificationService): void {
    if (error instanceof AuthenticationError) {
        service.show401Error();
    } else if (error instanceof AuthorizationError) {
        service.show403Error();
    } else if (error instanceof NetworkError) {
        service.showNetworkError();
    } else if (error instanceof ApiError) {
        service.showApiError(error.status, error.message);
    } else if (error instanceof Error) {
        service.showError(error.message);
    } else {
        service.showError('Unexpected error');
    }
}
