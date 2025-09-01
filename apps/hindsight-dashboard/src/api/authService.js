const API_BASE_URL = import.meta.env.VITE_HINDSIGHT_SERVICE_API_URL;

if (!API_BASE_URL) {
  throw new Error("Environment variable VITE_HINDSIGHT_SERVICE_API_URL is not defined.");
}

const authService = {
  // Get current user info from OAuth2 proxy
  getCurrentUser: async () => {
    const response = await fetch(`${API_BASE_URL}/user-info`, {
      credentials: 'include', // Include cookies for authentication
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        // User is not authenticated
        return { authenticated: false };
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  },

  // Check if user is authenticated
  isAuthenticated: async () => {
    try {
      const userInfo = await authService.getCurrentUser();
      return userInfo.authenticated;
    } catch (error) {
      console.error('Error checking authentication:', error);
      return false;
    }
  }
};

export default authService;
