from kube_eng.ansible.project.module_utils.s3_utils import S3Admin


def test_s3_validate(s3_admin: S3Admin):
    result = s3_admin.validate()
    assert result.validated, 'Connectivity and entitlements are validated'


def test_s3_bucket_create_and_remove(s3_admin: S3Admin):
    created = s3_admin.bucket_create('kube-eng-it')
    assert created.bucket_name == 'kube-eng-it', 'The bucket_name matches'
    assert created.changed, 'The bucket was created'
    assert s3_admin.bucket_exists('kube-eng-it'), 'The bucket exists after creation'

    recreated = s3_admin.bucket_create('kube-eng-it')
    assert not recreated.changed, 'Creating an existing bucket is a no-op'

    removed = s3_admin.bucket_remove('kube-eng-it')
    assert removed.changed, 'The bucket was removed'
    assert not s3_admin.bucket_exists('kube-eng-it'), 'The bucket no longer exists'

    reremoved = s3_admin.bucket_remove('kube-eng-it')
    assert not reremoved.changed, 'Removing an absent bucket is a no-op'
