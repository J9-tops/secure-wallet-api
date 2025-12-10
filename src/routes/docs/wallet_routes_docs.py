initiate_deposit_responses = {
    200: {
        "description": "Deposit Initiated Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Deposit Initiated",
                        "value": {
                            "reference": "TXN_1234567890ABCDEF",
                            "authorization_url": "https://checkout.paystack.com/abcd1234",
                        },
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Deposit Amount",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_amount": {
                        "summary": "Invalid Amount",
                        "value": {
                            "error": "INVALID_AMOUNT",
                            "message": "Invalid deposit amount",
                            "status_code": 400,
                            "errors": {"amount": ["Amount must be greater than zero"]},
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'deposit' permission"]},
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
                            "message": "Unable to process deposit. Please try again",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

initiate_deposit_custom_errors = ["400", "401", "500"]
initiate_deposit_custom_success = {
    "status_code": 200,
    "description": "Deposit initiated successfully.",
}

get_wallet_details_responses = {
    200: {
        "description": "Wallet Details Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Wallet Details",
                        "value": {
                            "wallet_number": "WLT1234567890AB",
                            "balance": 50000.00,
                            "created_at": "2025-01-01T10:00:00Z",
                            "updated_at": "2025-12-10T14:30:00Z",
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'read' permission"]},
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
                            "message": "Unable to retrieve wallet details",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

get_wallet_details_custom_errors = ["401", "500"]
get_wallet_details_custom_success = {
    "status_code": 200,
    "description": "Wallet details retrieved successfully.",
}

paystack_webhook_responses = {
    200: {
        "description": "Webhook Processed Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Webhook Processed",
                        "value": {"status": True},
                    },
                    "transaction_not_found": {
                        "summary": "Transaction Not Found (Acknowledged)",
                        "value": {
                            "status": "SUCCESS",
                            "status_code": 200,
                            "message": "Transaction not found, but webhook acknowledged",
                            "data": {"status": True, "note": "Transaction ignored"},
                        },
                    },
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Invalid Webhook Signature",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_signature": {
                        "summary": "Invalid Signature",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Invalid webhook signature",
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
                            "message": "Webhook processing failed",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

paystack_webhook_custom_errors = ["401", "500"]
paystack_webhook_custom_success = {
    "status_code": 200,
    "description": "Webhook processed successfully.",
}

get_deposit_status_responses = {
    200: {
        "description": "Deposit Status Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Deposit Status",
                        "value": {
                            "reference": "TXN_1234567890ABCDEF",
                            "status": "SUCCESS",
                            "amount": 10000.00,
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'read' permission"]},
                        },
                    },
                }
            }
        },
    },
    404: {
        "description": "Not Found - Transaction Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "transaction_not_found": {
                        "summary": "Transaction Not Found",
                        "value": {
                            "error": "NOT_FOUND",
                            "message": "Transaction not found",
                            "status_code": 404,
                            "errors": {"reference": ["Reference does not exist"]},
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
                            "message": "Unable to retrieve transaction status",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

get_deposit_status_custom_errors = ["401", "404", "500"]
get_deposit_status_custom_success = {
    "status_code": 200,
    "description": "Deposit status retrieved successfully.",
}

get_balance_responses = {
    200: {
        "description": "Balance Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Wallet Balance",
                        "value": {"balance": 50000.00},
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'read' permission"]},
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
                            "message": "Unable to retrieve balance",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}

get_balance_custom_errors = ["401", "500"]
get_balance_custom_success = {
    "status_code": 200,
    "description": "Balance retrieved successfully.",
}

transfer_funds_responses = {
    200: {
        "description": "Transfer Completed Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Transfer Success",
                        "value": {"status": "success", "message": "Transfer completed"},
                    }
                }
            }
        },
    },
    400: {
        "description": "Bad Request - Invalid Transfer Request",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_amount": {
                        "summary": "Invalid Amount",
                        "value": {
                            "error": "INVALID_REQUEST",
                            "message": "Invalid transfer request",
                            "status_code": 400,
                            "errors": {
                                "details": ["Transfer amount must be greater than zero"]
                            },
                        },
                    },
                    "insufficient_balance": {
                        "summary": "Insufficient Balance",
                        "value": {
                            "error": "INVALID_REQUEST",
                            "message": "Invalid transfer request",
                            "status_code": 400,
                            "errors": {
                                "details": [
                                    "Insufficient balance. Available: 1000.00, Required: 5000.00"
                                ]
                            },
                        },
                    },
                    "self_transfer": {
                        "summary": "Self Transfer Not Allowed",
                        "value": {
                            "error": "INVALID_REQUEST",
                            "message": "Invalid transfer request",
                            "status_code": 400,
                            "errors": {
                                "details": ["Cannot transfer to your own wallet"]
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'transfer' permission"]},
                        },
                    },
                }
            }
        },
    },
    404: {
        "description": "Not Found - Recipient Wallet Not Found",
        "content": {
            "application/json": {
                "examples": {
                    "wallet_not_found": {
                        "summary": "wallet Not Found",
                        "value": {
                            "error": "NOT_FOUND",
                            "message": "wallet not found",
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
                            "message": "Unable to retrieve transaction status",
                            "status_code": 500,
                            "errors": {},
                        },
                    },
                }
            }
        },
    },
}


transfer_funds_custom_errors = ["401", "500"]
transfer_funds_custom_success = {
    "status_code": 200,
    "description": "Balance retrieved successfully.",
}

get_transactions_responses = {
    200: {
        "description": "Transactions Retrieved Successfully",
        "content": {
            "application/json": {
                "examples": {
                    "success": {
                        "summary": "Transaction History",
                        "value": {
                            "transactions": [
                                {
                                    "id": "txn_12345",
                                    "user_id": "user_001",
                                    "reference": "REF-982347",
                                    "type": "credit",
                                    "amount": "5000.00",
                                    "status": "successful",
                                    "recipient_wallet_number": None,
                                    "recipient_user_id": None,
                                    "paystack_reference": None,
                                    "authorization_url": None,
                                    "created_at": "2025-12-10T10:30:00Z",
                                    "updated_at": "2025-12-10T10:30:00Z",
                                }
                            ],
                            "count": 1,
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
                    "insufficient_permissions": {
                        "summary": "Insufficient Permissions",
                        "value": {
                            "error": "UNAUTHORIZED",
                            "message": "Insufficient permissions",
                            "status_code": 401,
                            "errors": {"details": ["Requires 'read' permission"]},
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
                            "message": "Unable to retrieve transaction history",
                            "status_code": 500,
                            "errors": {},
                        },
                    }
                }
            }
        },
    },
}

get_transactions_custom_errors = ["401", "500"]
get_transactions_custom_success = {
    "status_code": 200,
    "description": "Transaction history retrieved successfully.",
}
