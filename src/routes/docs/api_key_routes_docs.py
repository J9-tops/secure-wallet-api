create_api_key_responses = {
    200: {
        "description": "API Key Created Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Created",
                        "value": {
                            "api_key": "<API_KEY>",
                            "expires_at": "2025-12-10T10:30:00Z",
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - API Key Creation Error",
        "content": {
            "application/json": {
                "examples": {
                    "max_keys_reached": {
                        "summary": "Maximum Active Keys Reached",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid API key request",
                            "status_code": 400,
                            "errors": {
                                "details": [
                                    "Maximum of 5 active API keys allowed per user"
                                ]
                            },
                        },
                    },
                    "invalid_permissions": {
                        "summary": "Invalid Permissions",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid API key request",
                            "status_code": 400,
                            "errors": {
                                "details": [
                                    "Invalid permission: admin. Must be one of {'deposit', 'transfer', 'read'}"
                                ]
                            },
                        },
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "not_authenticated": {
                        "summary": "User Not Authenticated",
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
                            "error": "SERVER_ERROR",
                            "message": "Failed to create API key. Please try again",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

create_api_key_custom_errors = ["400", "401", "500"]
create_api_key_custom_success = {
    "status_code": 200,
    "description": "API key created successfully.",
}

list_api_keys_responses = {
    200: {
        "description": "API Keys Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Keys List",
                        "value": {
                            "status": "SUCCESS",
                            "status_code": 200,
                            "message": "API keys retrieved successfully",
                            "data": {
                                "keys": [
                                    {
                                        "key_hash": "<KEY_HASH>",
                                        "key_prefix": "<API_KEY>",
                                        "is_active": True,
                                        "expires_at": "2025-12-11T11:44:35.415292+00:00",
                                        "created_at": "2025-12-10T11:44:29.500115+00:00",
                                        "user_id": "0dfbaeda-5455-4f42-8f22-c42587fa65a7",
                                        "id": "b332cdc6-9b07-4e3e-bbdf-e32ad261a214",
                                        "name": "Wallettt",
                                        "permissions": ["read", "transfer"],
                                        "is_revoked": False,
                                        "updated_at": "2025-12-10T11:44:29.500115+00:00",
                                    }
                                ],
                                "count": 1,
                            },
                        },
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "not_authenticated": {
                        "summary": "User Not Authenticated",
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
                            "error": "SERVER_ERROR",
                            "message": "Failed to retrieve API keys",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

list_api_keys_custom_errors = ["401", "500"]
list_api_keys_custom_success = {
    "status_code": 200,
    "description": "API keys retrieved successfully.",
}

revoke_api_key_responses = {
    200: {
        "description": "API Key Revoked Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Revoked",
                        "value": {
                            "status": "SUCCESS",
                            "status_code": 200,
                            "message": "API key revoked successfully",
                            "data": {"key_id": "<KEY_ID>"},
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Revocation Error",
        "content": {
            "application/json": {
                "examples": {
                    "already_revoked": {
                        "summary": "API Key Already Revoked",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid revocation request",
                            "status_code": 400,
                            "errors": {"details": ["API key is already revoked"]},
                        },
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "not_authenticated": {
                        "summary": "User Not Authenticated",
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
    404: {
        "description": "Not Found - API Key Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "key_not_found": {
                        "summary": "API Key Not Found",
                        "value": {
                            "error": "NOT_FOUND",
                            "message": "API key not found",
                            "status_code": 404,
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
                            "error": "SERVER_ERROR",
                            "message": "Failed to revoke API key. Please try again",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

revoke_api_key_custom_errors = ["400", "401", "404", "500"]
revoke_api_key_custom_success = {
    "status_code": 200,
    "description": "API key revoked successfully.",
}

rollover_api_key_responses = {
    200: {
        "description": "API Key Rolled Over Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "API Key Rolled Over",
                        "value": {
                            "api_key": "<NEW_API_KEY>",
                            "expires_at": "2026-01-10T10:30:00Z",
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Rollover Error",
        "content": {
            "application/json": {
                "examples": {
                    "key_not_expired": {
                        "summary": "API Key Not Expired Yet",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid rollover request",
                            "status_code": 400,
                            "errors": {"details": ["API key is not expired yet"]},
                        },
                    },
                    "key_already_revoked": {
                        "summary": "API Key Already Revoked",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid rollover request",
                            "status_code": 400,
                            "errors": {"details": ["API key has already been revoked"]},
                        },
                    },
                    "max_keys_reached": {
                        "summary": "Maximum Active Keys Reached",
                        "value": {
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid rollover request",
                            "status_code": 400,
                            "errors": {
                                "details": [
                                    "Maximum of 5 active API keys allowed per user"
                                ]
                            },
                        },
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication Required",
        "content": {
            "application/json": {
                "examples": {
                    "not_authenticated": {
                        "summary": "User Not Authenticated",
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
    404: {
        "description": "Not Found - API Key Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "key_not_found": {
                        "summary": "API Key Not Found",
                        "value": {
                            "error": "NOT_FOUND",
                            "message": "API key not found",
                            "status_code": 404,
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
                            "error": "SERVER_ERROR",
                            "message": "Failed to rollover API key. Please try again",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

rollover_api_key_custom_errors = ["400", "401", "404", "500"]
rollover_api_key_custom_success = {
    "status_code": 200,
    "description": "API key rolled over successfully.",
}
