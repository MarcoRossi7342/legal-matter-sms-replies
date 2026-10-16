import uvicorn


if __name__ == "__main__":
    uvicorn.run("legal_sms.inbound_service:service", host="127.0.0.1", port=8000, reload=False)

