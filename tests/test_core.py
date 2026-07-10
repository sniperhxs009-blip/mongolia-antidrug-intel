"""基础校验用测试用例"""
from config.core_official import is_forbidden_url
def test_blacklist():
    assert is_forbidden_url("https://police.gov.mn") == True
    assert is_forbidden_url("https://montsame.mn") == False
    assert is_forbidden_url("https://gogo.mn") == False
    print("黑白名单校验通过")
if __name__ == "__main__":
    test_blacklist()
