import python_jwt as jwt
import jwcrypto.jwk as jwk
import settings


def verify(token: str) -> dict | None:
    """
    The verify function takes a token as an argument and returns the claims
    if the token is valid, otherwise it returns None.


    :param token: str: Pass in the jwt token
    :return: A dictionary of claims if the token is valid, or none otherwise
    :doc-author: Trelent
    """
    if settings.JWT_PUBLIC_KEY or settings.JWT_SECRET:
        try:
            claims = None
            if settings.JWT_PUBLIC_KEY:
                with open(settings.JWT_PUBLIC_KEY, "rb") as pub_key:
                    (_header, claims) = jwt.verify_jwt(token, pub_key=jwk.JWK.from_pem(pub_key.read()),
                                                       allowed_algs=[settings.JWT_ALGORITHM or "RS256"], checks_optional=True)
            else:
                (_header, claims) = jwt.verify_jwt(token, pub_key=jwk.JWK.from_password(settings.JWT_SECRET),
                                                   allowed_algs=[settings.JWT_ALGORITHM or "HS256"], checks_optional=True)
            return claims
        except Exception:
            return None
    else:
        return None
