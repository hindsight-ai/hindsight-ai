# Hindsight AI Authentication Flow with Cloudflare, Traefik, and OAuth2 Proxy

This diagram illustrates the authentication flow when a user attempts to access your Hindsight AI Dashboard (e.g., `https://www.hindsight-ai.com`) through Cloudflare, protected by `oauth2-proxy` and Google authentication.

```mermaid
sequenceDiagram
    actor User
    participant Cloudflare
    participant ServerIP as Your Server (46.62.141.65)
    participant Traefik
    participant OAuth2Proxy as OAuth2 Proxy
    participant Google
    participant HindsightDashboard as Hindsight Dashboard
    participant HindsightService as Hindsight Service

    User->>Cloudflare: 1. Request https://www.hindsight-ai.com
    Cloudflare->>ServerIP: 2. Proxy request (Host: www.hindsight-ai.com)
    ServerIP->>Traefik: 3. Request received by Traefik (via IngressRoute)

    alt First Access / Not Authenticated
        Traefik->>OAuth2Proxy: 4. Forward request to OAuth2 Proxy (via oauth2-proxy-auth middleware)
        OAuth2Proxy->>User: 5. Redirect to Google Login (HTTP 302)
        User->>Google: 6. User logs in with Google
        Google->>OAuth2Proxy: 7. Redirect back to OAuth2 Proxy with auth code
        OAuth2Proxy->>Google: 8. Exchange auth code for tokens
        Google-->>OAuth2Proxy: 9. Return tokens
        OAuth2Proxy->>OAuth2Proxy: 10. Verify user email (e.g., ibarz.jean@gmail.com)
        alt Email Authorized
            OAuth2Proxy->>User: 11. Set authentication cookie
            OAuth2Proxy->>Traefik: 12. Allow request to proceed
            Traefik->>HindsightDashboard: 13. Route request to Hindsight Dashboard Service
            HindsightDashboard-->>Traefik: 14. Serve Dashboard content
            Traefik-->>Cloudflare: 15. Return Dashboard content
            Cloudflare-->>User: 16. Display Dashboard
        else Email Not Authorized
            OAuth2Proxy->>User: 11. Deny access / Show error page
        end
    else Already Authenticated
        Traefik->>OAuth2Proxy: 4. Forward request to OAuth2 Proxy (with existing cookie)
        OAuth2Proxy->>OAuth2Proxy: 5. Validate authentication cookie
        OAuth2Proxy->>Traefik: 6. Allow request to proceed
        alt Request to Dashboard
            Traefik->>HindsightDashboard: 7. Route request to Hindsight Dashboard Service
            HindsightDashboard-->>Traefik: 8. Serve Dashboard content
            Traefik-->>Cloudflare: 9. Return Dashboard content
            Cloudflare-->>User: 10. Display Dashboard
        else Request to API
            Traefik->>HindsightService: 7. Route request to Hindsight Service
            HindsightService-->>Traefik: 8. Serve API response
            Traefik-->>Cloudflare: 9. Return API response
            Cloudflare-->>User: 10. Return API response
        end
    end
```

**Explanation of the flow:**

1.  **User Request:** The user types `https://www.hindsight-ai.com` into their browser.
2.  **Cloudflare Proxy:** Cloudflare, acting as a reverse proxy (due to the orange cloud DNS setting), intercepts this request. It resolves your domain to your server's IP address (`46.62.141.65`) and forwards the request to your server. Crucially, Cloudflare maintains the original `Host` header (`www.hindsight-ai.com`).
3.  **Traefik Ingress:** Your server receives the request, and Traefik, as your Kubernetes Ingress Controller, picks it up. The `IngressRoute` for `hindsight-dashboard-ingress-domain` matches the `Host` header (`www.hindsight-ai.com`).
4.  **OAuth2 Proxy Middleware:** Before routing the request to the Hindsight Dashboard service, Traefik applies the `oauth2-proxy-auth` middleware. This middleware tells Traefik to send the request to the `oauth2-proxy-service` (internally on port `4180`) for an authentication check.
5.  **Authentication Check (First Access):**
    *   If the user is not authenticated (no valid `oauth2-proxy` cookie), `oauth2-proxy` generates a Google login URL and sends a `302 Redirect` response back to the user's browser.
    *   The user's browser then redirects to Google's authentication page.
    *   After the user successfully logs in with their Google account, Google redirects the user's browser back to `oauth2-proxy`'s callback URL (`https://www.hindsight-ai.com/oauth2/callback`) with an authorization code.
    *   `oauth2-proxy` exchanges this code with Google for user tokens and then verifies the user's email address against the allowed list (e.g., `ibarz.jean@gmail.com`).
    *   If the email is authorized, `oauth2-proxy` sets a secure authentication cookie in the user's browser and then signals Traefik to allow the original request to proceed.
6.  **Authentication Check (Subsequent Access):**
    *   If the user already has a valid `oauth2-proxy` cookie, Traefik still forwards the request to `oauth2-proxy`.
    *   `oauth2-proxy` validates the existing cookie. If valid, it immediately signals Traefik to allow the request to proceed without redirecting to Google.
7.  **Dashboard Access:** Once `oauth2-proxy` authorizes the request, Traefik routes the request to the `hindsight-dashboard-service`. The dashboard serves its content, which is then passed back through Traefik and Cloudflare to the user's browser.

This entire process ensures that only pre-approved Google accounts can access your Hindsight AI Dashboard and API.
