from unittest import mock


def patch_feature_flag(*flag_names, up=True):
    from share.models.feature_flag import FeatureFlag
    _old_isup = FeatureFlag.objects.flag_is_up

    def _patched_isup(flag_name):
        if flag_name in flag_names:
            return up
        return _old_isup(flag_name)
    return mock.patch.object(FeatureFlag.objects, 'flag_is_up', new=_patched_isup)
