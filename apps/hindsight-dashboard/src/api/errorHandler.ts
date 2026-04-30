import notificationService from '../services/notificationService';
import { ApiError, AuthenticationError, AuthorizationError, NetworkError } from './errors';

export function showErrorToast(error: unknown): void {
    if (error instanceof AuthenticationError) {
        notificationService.show401Error();
    } else if (error instanceof AuthorizationError) {
        notificationService.showApiError('Permission denied. Contact your administrator.');
    } else if (error instanceof NetworkError) {
        notificationService.showNetworkError();
    } else if (error instanceof ApiError) {
        notificationService.showApiError(error.message);
    } else if (error instanceof Error) {
        notificationService.showApiError(error.message);
    } else {
        notificationService.showApiError('Unexpected error');
    }
}
