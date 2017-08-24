import argparse
import datetime
import logging
import os
import re
import subprocess
import time

import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import NoSuchbucket
from requests import ConnectionError
from requests.models import ChunkedEncodingError
from retry import retry

s3 = boto3.resource('s3', endpoint_url='http://sreport.scality.com')


STAGING_ARTIFACTS_PREFIX = os.getenv('ARTIFACTS_PREFIX')
PROMOTED_ARTIFACTS_PREFIX = os.getenv('PROMOTED_ARTIFACTS_PREFIX')

STAGING_REGEXP = (r"^((.*):)?%s[0-9]+(\.[0-9]+){1,3}\."
                  r"r([0-9]{12})\.([0-9a-f]+)(\.(.*)\.([0-9]+))?$" %
                  STAGING_ARTIFACTS_PREFIX)
PROMOTED_REGEXP = (r"^((.*):)?%s([^\-]+)$" %
                   PROMOTED_ARTIFACTS_PREFIX)

STAGING_REGEXP_COMPILED = re.compile(STAGING_REGEXP)
PROMOTED_REGEXP_COMPILED = re.compile(PROMOTED_REGEXP)


@retry((ConnectionError, ClientError), tries=3, delay=1, backoff=2)
def bucket_copy(src_bucket, dst_bucket_name):
    """Copy a CloudFiles bucket to another."""
    # check if dst_bucket_name matches a 'promoted' bucket
    if not PROMOTED_REGEXP_COMPILED.match(dst_bucket_name):
        logging.error("%s is not allowed to be a copy destination" %
                      dst_bucket_name)
        return

    stamp = ""
    try:
        stamp = src_bucket.fetch_object(".final_status")
    except Exception:
        pass
    if stamp != "SUCCESSFUL":
        logging.info("build failed or incomplete in bucket %s, skipping",
                     src_bucket.name)
        return
    logging.info(f"copying {src_bucket.name} to {dst_bucket_name}")
    new_bucket = s3.create_bucket(Bucket=dst_bucket_name)
    for obj in src_bucket.object.all():
        copy_source = {
            'Bucket': src_bucket.name,
            'Key': obj.name
        }
        new_bucket.copy(copy_source, obj.name)


@retry((ConnectionError, ClientError), tries=3, delay=1, backoff=2)
def bucket_delete_content(src_bucket):
    """Delete a CloudFiles bucket content."""
    # check if src_bucket.name matches a 'staging' bucket
    if not STAGING_REGEXP_COMPILED.match(src_bucket.name):
        logging.error("%s is not allowed to be deleted" % src_bucket.name)
        return

    logging.info(f"deleting {src_bucket.name} content")
    return src_bucket.objects.all().delete()


@retry((ConnectionError, ClientError), tries=3, delay=1, backoff=2)
def bucket_delete(src_bucket):
    """Delete an empty CloudFiles bucket."""
    # check if src_bucket matches a 'staging' bucket
    if not STAGING_REGEXP_COMPILED.match(src_bucket):
        logging.error(f"{src_bucket} is not allowed to be deleted")
        return

    logging.info("deleting %s", src_bucket)
    return src_bucket.delete()


def bucket_commit_time(bucket):
    """Give the commit time of a staging bucket."""
    items = get_staging_items(bucket.name)
    if items:
        return items['timestamp']
    return None


def extract_date_from_meta(bucket, obj):
    try:
        meta, _ = bucket.fetch_object(obj, include_meta=True)
        ts = datetime.datetime.utcfromtimestamp(float(meta['X-Timestamp']))
        return ts.strftime('%y%m%d%H%M%S')
    except Exception:
        return None


def is_bucket_content_deprecated(bucket, expiration_time_str):
    """True only if an object is found and is older than expiration time."""
    # First, try ".final_status" object to possibly save a get_objects() call
    obj_date = extract_date_from_meta(bucket, ".final_status")
    if obj_date:
        return obj_date < expiration_time_str

    # Something was wrong for ".final_status", try an objet from get_objects()
    objs = bucket.get_objects(limit=1)
    if objs:
        obj_date = extract_date_from_meta(bucket, objs[0].name)
        if obj_date:
            return obj_date < expiration_time_str

    return False


@retry(exceptions=Exception, tries=3, delay=1, backoff=2)
def run_command(args):
    return subprocess.check_output(args, shell=True)


def get_git_repo_tags(repo):
    m = re.search(r"^([^\./]+):([^\./]+):([^\./]+)$", repo)
    if not m:
        logging.error("repo '%s' is malformed, skipping", repo)
        return []

    git_host = m.group(1)
    git_owner = m.group(2)
    git_slug = m.group(3)

    if git_host == 'bitbucket':
        git_host_fqdn = "{{ pillar['bitbucket']['hostname'] }}"
    elif git_host == 'github':
        git_host_fqdn = "{{ pillar['github']['hostname'] }}"
    else:
        logging.error("unknown fqdn for git host '%s', skipping", git_host)
        return []

    repo_dir = '/root/gitcache/%s/%s/%s' % (git_host, git_owner, git_slug)

    if os.path.isdir(repo_dir):
        logging.info("removing local tags from repo '%s'" % repo)
        run_command('git -C ' + repo_dir + ' tag -l | '
                    'xargs git -C ' + repo_dir + ' tag -d')
        logging.info("collecting garbage in repo '%s'" % repo)
        run_command('git -C ' + repo_dir + ' gc')
        logging.info("fetching repo '%s'" % repo)
        run_command('git -C ' + repo_dir + ' fetch')
    else:
        logging.info("cloning repo '%s'" % repo)
        run_command('git clone git@%s:%s/%s.git ' %
                    (git_host_fqdn, git_owner, git_slug) + repo_dir)
    logging.info("repo '%s' is up to date" % repo)

    command_output = run_command('git -C ' + repo_dir +
                                 ' show-ref --tags --abbrev || true')

    repo_tags_list = []
    lines = command_output.splitlines()
    for line in lines:
        m = re.search(r"^([0-9a-f]+)\s+refs/tags/(.*)$", line)
        if not m:
            logging.error("could not parse git show-ref output")
            continue

        tag_hash = m.group(1)
        tag_name = m.group(2)

        if '-' in tag_name or '/' in tag_name:
            logging.error("can not promote '%s' tag "
                          "(it must not contain '-' or '/' characters)",
                          tag_name)
            continue

        command_output = run_command('git -C ' + repo_dir +
                                     ' cat-file -p ' + tag_name)

        b4nb = ""
        m = re.search(r"\ntag %s\ntagger (.*)\n\n.*%%([0-9]+).*$" % tag_name,
                      command_output, re.MULTILINE)
        if m:
            b4nb = m.group(2)
            b4nb = b4nb.zfill(8)

            real_tag_hash = run_command('git -C ' + repo_dir +
                                        ' show-ref --tags -d --abbrev ' +
                                        tag_name)
            n = re.search(r"\n([0-9a-f]+)\srefs/tags/%s\^\{\}" % tag_name,
                          real_tag_hash)
            if n:
                tag_hash = n.group(1)

        repo_tags_list.append((tag_hash, tag_name, b4nb))

    return repo_tags_list


def get_staging_items(bucket_name):
    m = STAGING_REGEXP_COMPILED.search(bucket_name)
    if not m:
        return None

    repo = m.group(2)
    if not repo:
        repo = "bitbucket:scality:ring"

    timestamp = m.group(4)

    git_hash = m.group(5)

    stagename = m.group(7)
    if not stagename:
        stagename = "pre-merge"

    b4nb = m.group(8)
    if not b4nb:
        b4nb = ""

    return {"repo": repo,
            "timestamp": timestamp,
            "git_hash": git_hash,
            "stagename": stagename,
            "b4nb": b4nb}


def get_promoted_items(bucket_name):
    m = PROMOTED_REGEXP_COMPILED.search(bucket_name)
    if not m:
        return None

    repo = m.group(2)
    if not repo:
        repo = "bitbucket:scality:ring"

    git_tag = m.group(3)

    return {"repo": repo,
            "git_tag": git_tag}


def get_all_git_tags(staging_buckets_list, promoted_buckets_list):
    """List the git tags."""
    repo_list = []
    for bucket in staging_buckets_list:
        items = get_staging_items(bucket.name)
        if items and items['repo'] not in repo_list:
            repo_list.append(items['repo'])
    for bucket in promoted_buckets_list:
        items = get_staging_items(bucket.name)
        if items and items['repo'] not in repo_list:
            repo_list.append(items['repo'])

    tags_list = {}
    for repo in repo_list:
        tags_list[repo] = get_git_repo_tags(repo)

    return tags_list


@retry((ConnectionError, ClientError), tries=3, delay=1, backoff=2)
def get_buckets(prefix=None, match=None):
    """List the buckets."""
    buckets_list = s3.buckets.all()
    if match:
        return [bucket for bucket in buckets_list if match.match(bucket.name)]
    return buckets_list


def get_expiration_time(ttl=0):
    staging_max_age = int(os.getenv("STAGING_MAX_AGE", "14")) - ttl

    if staging_max_age <= 0:
        raise Exception("STAGING_MAX_AGE (%d) - ttl (%d) "
                        "must be greater than 0",
                        staging_max_age, ttl)

    expiration_time = datetime.datetime.now() - \
        datetime.timedelta(days=staging_max_age)
    return expiration_time.strftime('%y%m%d%H%M%S')


def promote(staging_buckets_list, promoted_buckets_list):

    # Get buckets that have at least still one day to live
    expiration_time_str = get_expiration_time(ttl=1)

    tags_list = get_all_git_tags(staging_buckets_list,
                                 promoted_buckets_list)
    repos = tags_list.keys()

    for repo in repos:
        logging.info("processing repo '%s'", repo)
        for tag_hash, tag_name, b4nb in tags_list[repo]:
            logging.info("processing tag '%s' (short hash '%s', b4nb '%s')",
                         tag_name, tag_hash, b4nb)

            logging.info("checking if tag '%s' is already promoted",
                         tag_name)

            # Check if this tag has been promoted
            skip_it = False
            for bucket in promoted_buckets_list:
                items = get_promoted_items(bucket.name)
                if (items and
                   items['repo'] == repo and
                   items['git_tag'] == tag_name):
                    skip_it = True
                    break
            if skip_it:
                logging.info("=> skipping")
                continue

            logging.info("=> no '%s' promoted bucket found", tag_name)

            # Check if this tag is in staging or promoted buckets
            logging.info(f"checking if tag '{tag_name}' is in staging buckets")

            src_bucket = None
            for bucket in staging_buckets_list:
                items = get_staging_items(bucket.name)
                if (items and
                   items['repo'] == repo and
                   items['stagename'] == 'pre-merge' and
                   items['git_hash'] == tag_hash and
                   items['b4nb'] == b4nb and
                   not is_bucket_content_deprecated(bucket,
                                                    expiration_time_str)):
                    src_bucket = bucket
                    break

            if not src_bucket:
                logging.info("=> no staging bucket to promote tag"
                             " '%s'", tag_name)
                logging.info("checking if tag '%s' is in promoted "
                             "buckets",
                             tag_name)
                for other_tag_hash, other_tag_name, b4nb in tags_list[repo]:
                    if (other_tag_hash == tag_hash and
                       other_tag_name != tag_name):
                        for bucket in promoted_buckets_list:
                            items = get_promoted_items(bucket.name)
                            if (items and
                               items['repo'] == repo and
                               items['git_tag'] == other_tag_name):
                                src_bucket = bucket
                                break

            if not src_bucket:
                logging.info("=> no promoted bucket to promote tag"
                             " '%s'", tag_name)
                continue

            promoted_bucket_name = (f'{repo}:{PROMOTED_ARTIFACTS_PREFIX}'
                                    f'{tag_name}')
            logging.info("=> promoting tag (copying %s to %s)",
                         src_bucket.name, promoted_bucket_name)
            bucket_copy(src_bucket, promoted_bucket_name)
        logging.info("repo '%s' processed", repo)


def deprecate(staging_buckets_list):
    staging_min_keep_nb = int(os.getenv("STAGING_MIN_KEEP", "1000"))
    staging_max_pass_nb = int(os.getenv("STAGING_MAX_PASS", "100"))

    if staging_min_keep_nb <= 0:
        raise Exception("STAGING_MIN_KEEP (%d) must be greater than 0",
                        staging_min_keep_nb)
    if staging_max_pass_nb <= 0:
        raise Exception("STAGING_MAX_PASS (%d) must be greater than 0",
                        staging_max_pass_nb)
    if staging_min_keep_nb <= staging_max_pass_nb:
        raise Exception("STAGING_MIN_KEEP (%d) must be greater than "
                        "STAGING_MAX_PASS (%d)",
                        staging_min_keep_nb, staging_max_pass_nb)

    # Get the most recent commit date for expired buckets
    expiration_time_str = get_expiration_time()

    # Check if the deprecation pass mut go further
    nb_staging_buckets = len(staging_buckets_list)
    if nb_staging_buckets < staging_min_keep_nb:
        # Skip cleanup, too few staging buckets
        logging.info("%d staging buckets found, below trigger (%d): "
                     "no cleanup",
                     nb_staging_buckets, staging_min_keep_nb)
        return

    # Sort the staging bucket by commit time
    sorted_staging_buckets_list = sorted(staging_buckets_list,
                                         key=bucket_commit_time)

    # Loop on the clean sorted list to delete buckets content
    deleted_buckets = 0
    deleted_buckets_handlers = []
    for staging_bucket in sorted_staging_buckets_list:

        if bucket_commit_time(staging_bucket) > expiration_time_str:
            # Staging bucket too recent, no need to go further in list
            logging.info("bucket '%s' is too recent",
                         staging_bucket.name)
            break

        if not is_bucket_content_deprecated(staging_bucket,
                                            expiration_time_str):
            continue

        # Staging bucket must be deleted
        deleted_buckets += 1
        logging.info("bucket '%s' is matching cleanup criterias (%d/%d)",
                     staging_bucket.name,
                     deleted_buckets, staging_max_pass_nb)
        try:
            delete_handler = bucket_delete_content(staging_bucket)
            deleted_buckets_handlers.append(delete_handler)
        except (ClientError, ChunkedEncodingError):
            pass

        # Exit loop if at least staging_max_pass_nb buckets were deleted
        if deleted_buckets >= staging_max_pass_nb:
            break

    # Loop on the selected buckets to delete buckets when empty
    buckets_checked_incr = 0
    buckets_checked_max = len(deleted_buckets_handlers)
    delete_pass_incr = 0
    delete_pass_max = 3600*2  # approx 2 hours
    if deleted_buckets_handlers:
        logging.info("waiting for buckets contents to be deleted")
    while deleted_buckets_handlers:
        delete_handler = deleted_buckets_handlers.pop(0)

        logging.debug("checking bucket '%s'", delete_handler.bucket)
        if delete_handler.completed:
            try:
                bucket_delete(delete_handler.bucket)
            except (NoSuchbucket, ClientError, ChunkedEncodingError):
                pass
        else:
            deleted_buckets_handlers.append(delete_handler)

        buckets_checked_incr += 1
        if buckets_checked_incr >= buckets_checked_max:
            delete_pass_incr += 1
            if delete_pass_incr >= delete_pass_max:
                logging.error("deprecation pass took too long, exiting")
                break
            buckets_checked_incr = 0
            buckets_checked_max = len(deleted_buckets_handlers)
            logging.debug("sleeping 1 second")
            time.sleep(1)


def run_pass(promotion_only, expiration_only):
    # Define logging level
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("requests.packages.urllib3").setLevel(logging.ERROR)

    # Get all buckets
    staging_buckets_list = get_buckets(match=STAGING_REGEXP_COMPILED)
    promoted_buckets_list = get_buckets(match=PROMOTED_REGEXP_COMPILED)

    # bucket promotion
    if not expiration_only:
        logging.info("starting promotion pass")
        promote(staging_buckets_list, promoted_buckets_list)
        logging.info("promotion pass finished")

    # bucket deprecation
    if not promotion_only:
        logging.info("starting deprecation pass")
        deprecate(staging_buckets_list)
        logging.info("deprecation pass finished")


def main():
    # Get args
    parser = argparse.ArgumentParser()
    parser.add_argument('--promotion-only', action='store_true')
    parser.add_argument('--expiration-only', action='store_true')
    args = parser.parse_args()

    # Check args consistency
    if args.promotion_only and args.expiration_only:
        raise Exception("can not set both --promotion-only "
                        "and --expiration-only flags in the same time")

    # Call pass
    run_pass(args.promotion_only, args.expiration_only)


if __name__ == '__main__':
    main()
