from fastapi.responses import JSONResponse


def api_success(data=None):

    return {
        "success": True,
        "data": data
    }



def api_error(
    code: str,
    message: str,
    status_code: int = 400
):

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "code": code,
            "message": message
        }
    )
