from app.checker.prize_rules import PrizeRuleService


def test_prize_rule_mapping():
    service = PrizeRuleService({"third": 3000, "fourth": 200, "fifth": 10, "sixth": 5})
    assert service.resolve_prize(6, True)[0] == "first"
    assert service.resolve_prize(6, False)[0] == "second"
    assert service.resolve_prize(5, True) == ("third", 3000)
    assert service.resolve_prize(4, True) == ("fourth", 200)
    assert service.resolve_prize(3, True) == ("fifth", 10)
    assert service.resolve_prize(1, True) == ("sixth", 5)
    assert service.resolve_prize(3, False) == (None, None)
