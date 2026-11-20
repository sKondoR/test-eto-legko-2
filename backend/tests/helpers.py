from app.domain.offers import OfferShare


def shares(*pairs: tuple[int, int]) -> tuple[OfferShare, ...]:
    return tuple(OfferShare(offer_id, share) for offer_id, share in pairs)
