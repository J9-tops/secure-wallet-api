google_login_responses = {
    200: {
        "description": "Google OAuth URL Generated Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Authorization URL",
                        "value": {
                            "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
                            "state": "random_state_string_for_csrf_protection",
                        },
                    }
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "config_error": {
                        "summary": "OAuth Configuration Error",
                        "value": {
                            "error": "CONFIGURATION_ERROR",
                            "message": "Google OAuth configuration error",
                            "status_code": 500,
                            "errors": {
                                "details": ["Google OAuth credentials not configured"]
                            },
                        },
                    },
                    "server_error": {
                        "summary": "Server Error",
                        "value": {
                            "error": "SERVER_ERROR",
                            "message": "Authentication service temporarily unavailable",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

google_login_custom_errors = ["500"]
google_login_custom_success = {
    "status_code": 200,
    "description": "Google OAuth authorization URL generated successfully.",
}

google_callback_responses = {
    200: {
        "description": "Authentication Successful - JWT Token Issued",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "JWT Token",
                        "value": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid OAuth Request",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_code": {
                        "summary": "Invalid Authorization Code",
                        "value": {
                            "error": "INVALID_REQUEST",
                            "message": "Invalid authentication request",
                            "status_code": 400,
                            "errors": {
                                "details": ["Failed to exchange authorization code"]
                            },
                        },
                    },
                    "missing_user_info": {
                        "summary": "Invalid User Info",
                        "value": {
                            "error": "INVALID_REQUEST",
                            "message": "Invalid authentication request",
                            "status_code": 400,
                            "errors": {"details": ["Invalid user info from Google"]},
                        },
                    },
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "server_error": {
                        "summary": "Server Error",
                        "value": {
                            "error": "SERVER_ERROR",
                            "message": "Authentication failed. Please try again",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

google_callback_custom_errors = ["400", "500"]
google_callback_custom_success = {
    "status_code": 200,
    "description": "Authentication successful. JWT token issued.",
}

test_token_responses = {
    200: {
        "description": "Token Valid - User Information Retrieved",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Valid Token",
                        "value": {
                            "status": "SUCCESS",
                            "status_code": 200,
                            "message": "Token is valid!",
                            "data": {
                                "user": {
                                    "id": "user_123e4567-e89b-12d3-a456-426614174000",
                                    "email": "user@example.com",
                                    "name": "John Doe",
                                }
                            },
                        },
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Invalid or Missing Token",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_token": {
                        "summary": "Invalid Token",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Authentication required",
                            "status_code": 401,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "examples": {
                    "server_error": {
                        "summary": "Server Error",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Failed to validate token",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

test_token_custom_errors = ["401", "500"]
test_token_custom_success = {
    "status_code": 200,
    "description": "Token is valid.",
}
