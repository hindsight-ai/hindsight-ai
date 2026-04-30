export class ApiError extends Error {
    constructor(public readonly status: number, message: string, public readonly body?: unknown) {
        super(message);
        this.name = 'ApiError';
    }
}

export class AuthenticationError extends ApiError {  // 401
    constructor(body?: unknown) {
        super(401, 'Authentication required', body);
        this.name = 'AuthenticationError';
    }
}

export class AuthorizationError extends ApiError {   // 403
    constructor(body?: unknown) {
        super(403, 'Permission denied', body);
        this.name = 'AuthorizationError';
    }
}

export class NetworkError extends Error {
    constructor(message = 'Network error', public readonly cause?: unknown) {
        super(message);
        this.name = 'NetworkError';
    }
}
