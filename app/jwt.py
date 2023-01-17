import python_jwt as jwt, jwcrypto.jwk as jwk
import settings


def verify(token: str) -> dict | None:
    if settings.JWT_PUBLIC_KEY or settings.JWT_SECRET:
        try:
            (_header, claims) = jwt.verify_jwt(token, pub_key=jwk.JWK.from_pem(open(settings.JWT_PUBLIC_KEY, "rb").read())
                       if settings.JWT_PUBLIC_KEY else jwk.JWK.from_password(settings.JWT_SECRET),
                       allowed_algs=[settings.JWT_ALGORITHM or
                       ("RS256" if settings.JWT_PRIVATE_KEY else "HS256")], checks_optional=True)
            return claims
        except:
            return None
    else:
        return None
