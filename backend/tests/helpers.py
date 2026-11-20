from app.domain.offers import OfferShare
from app.domain.plan import Placement

# ID из ответов живого трекера (домен kylovoa.com, группа и источник FORTESTS) — только для
# тестов. Рабочие домен, группа и источник задаются в .env по именам.
PLACEMENT = Placement(domain_id=1813, group_id=10332, traffic_source_id=836)


def shares(*pairs: tuple[int, int]) -> tuple[OfferShare, ...]:
    return tuple(OfferShare(offer_id, share) for offer_id, share in pairs)
