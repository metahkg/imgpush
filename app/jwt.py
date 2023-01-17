import python_jwt as jwt
import settings


def verify(token: str) -> dict | None:
    if settings.JWT_PUBLIC_KEY or settings.JWT_SECRET:
        try:
            (_header, claims) = jwt.verify_jwt(token, pub_key=open(settings.JWT_PUBLIC_KEY).read()
                       if settings.JWT_PUBLIC_KEY else settings.JWT_SECRET,
                       allowed_algs=[settings.JWT_ALGORITHM or
                       ("RS256" if settings.JWT_PRIVATE_KEY else "HS256")])
            return claims
        except:
            return None
    else:
        return None
