--
--
-- Compute S3 signature
--
--


local aws_bucket_prefix = os.getenv('AWS_BUCKET_PREFIX')
local build_prefixes = { "dev%-", "preprod%-", "" }


-- Get encoded key.
--
local function get_encoded_key (key)
  return key:gsub(' ', '%%20')
end


-- Get encoded prefix.
--
local function get_encoded_prefix (prefix)
  -- If the prefix is empty, this means are browsing the root directory. But
  -- as we do not want to list the artifacts for every project, we set the
  -- prefix to a value that will match only builds for the current project.
  -- This value can be computed from the ingress in the "Script-Name" HTTP
  -- header.
  --
  if prefix == "" and ngx.var.http_script_name ~= nil then
    prefix = string.match(ngx.var.http_script_name, "[^/]+/[^/]+/[^/]+/"):gsub("/", ":")
  end
  return ngx.escape_uri(prefix)
end


-- Check if this is a promoted build.
--
local function is_promoted(build_name)
  for i=1, #build_prefixes do
    if build_name:match("^[a-z]+:[a-z]+:[%-A-Za-z0-9]+:" .. build_prefixes[i] .. "promoted%-") then
      return true
    end
  end
  return false
end


-- Check if this is a staging build (with no expiration disabled).
--
local function is_staging (build_name)
  for i=1, #build_prefixes do
    if build_name:match("^[a-z]+:[a-z]+:[%-A-Za-z0-9]+:" .. build_prefixes[i] .. "staging%-") then
      return true
    end
  end
  return false
end


-- Set the target bucket.
--
local function scan_tgt_buckets (build_tgt)
  if ngx.var.aws_tgt_bucket == "" then
    if is_promoted(build_tgt) then
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-promoted"
    elseif is_staging(build_tgt) then
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
    else
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-prolonged"
    end
  end
end


-- Replace nil by an empty string.
--
local function empty_if_nil (str)
  if str == nil then
    return ""
  end
  return str
end


-- Compute AWS S3 signature with an explicit canonicalized resource.
-- Used by multipart modes that need to append subresource query params.
--
local function compute_S3_signature_with_resource (canonicalized_amz_headers, canonicalized_resource)
  local aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
  local http_content_md5 = empty_if_nil(ngx.var.http_content_md5)
  local http_content_type = empty_if_nil(ngx.var.http_content_type)
  local http_date = empty_if_nil(ngx.var.http_date)
  local string_to_sign = ngx.var.request_method .. "\n" .. http_content_md5 .. "\n" .. http_content_type .. "\n" .. http_date .. "\n" .. canonicalized_amz_headers .. "\n" .. canonicalized_resource
  ngx.var.aws_signature = ngx.encode_base64(ngx.hmac_sha1(aws_secret_key, string_to_sign))
end


-- Compute AWS S3 signature.
--
local function compute_S3_signature (canonicalized_amz_headers)
  local canonicalized_resource = "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key
  compute_S3_signature_with_resource(canonicalized_amz_headers, canonicalized_resource)
end


-- Compute AWS S3 presignature.
--
local function compute_S3_presignature (expires)
  local canonicalized_resource = "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key
  local aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
  local http_content_md5 = empty_if_nil(ngx.var.http_content_md5)
  local http_content_type = empty_if_nil(ngx.var.http_content_type)
  local string_to_sign = ngx.var.request_method .. "\n" .. http_content_md5 .. "\n" .. http_content_type .. "\n" .. expires .. "\n" .. canonicalized_resource
  local aws_signature = ngx.encode_base64(ngx.hmac_sha1(aws_secret_key, string_to_sign))
  ngx.var.presign_query_string = ngx.encode_args({['AWSAccessKeyId'] = ngx.var.aws_access_key, ['Signature'] = aws_signature, ['Expires'] = expires})
end


-- Get mode set by nginx conf.
--
local signature_mode = ngx.var.signature_mode
if signature_mode == nil or signature_mode == "" then
  ngx.log(ngx.ERR, "no signature_mode specified")
end


-- init
--
ngx.var.x_amz_date = ngx.http_time(ngx.time())
ngx.var.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')


-- do specific stuff regarding the signature mode
--
if signature_mode == "UPLOAD" then

  -- UPLOAD is only done on staging
  --
  local build_tgt

  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  build_tgt = ngx.var.canonical_path:match("^[^/]+")

  -- Set the target bucket.
  --
  if ngx.var.aws_tgt_bucket == "" then
    ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
  end

  -- Set the amz headers.
  --
  ngx.var.x_amz_acl = "private"

  -- Compute signature.
  --
  compute_S3_signature ("x-amz-acl:" .. ngx.var.x_amz_acl .. "\nx-amz-date:" .. ngx.var.x_amz_date)

elseif signature_mode == "LISTING" then

  -- LISTING mode.
  --
  local build_tgt

  ngx.var.encoded_key = ""
  ngx.var.encoded_prefix = get_encoded_prefix(ngx.var.canonical_path)
  build_tgt = ngx.var.canonical_path:match("^[^/]+")

  -- Set the target bucket.
  --
  if build_tgt ~= nil then
    scan_tgt_buckets(build_tgt)
  end

  -- Compute signature.
  --
  compute_S3_signature ("x-amz-date:" .. ngx.var.x_amz_date)

elseif signature_mode == "DOWNLOAD" then

  -- DOWNLOAD mode.
  --
  local build_tgt

  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  build_tgt = ngx.var.canonical_path:match("^[^/]+")

  -- Set the target bucket, if there is a build in canonical_path.
  --
  scan_tgt_buckets(build_tgt)

  -- Compute signature.
  --
  compute_S3_signature ("x-amz-date:" .. ngx.var.x_amz_date)

elseif signature_mode == "COPY" then

  -- COPY mode.
  --

  local build_src, build_tgt, aws_src_bucket

  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path:match("^[^/]+/(.*)"))
  build_src, build_tgt = ngx.var.canonical_path:match("^([^/]+)/([^/]+)")

  -- Set the source bucket.
  --
  if is_staging(build_src) then
    aws_src_bucket = aws_bucket_prefix .. "-staging"
  elseif is_promoted(build_src) then
    aws_src_bucket = aws_bucket_prefix .. "-promoted"
  else
    aws_src_bucket = aws_bucket_prefix .. "-prolonged"
  end

  -- Set the target bucket.
  --
  if ngx.var.aws_tgt_bucket == "" then
    if is_staging(build_tgt) then
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
    elseif is_promoted(build_tgt) then
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-promoted"
    else
      ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-prolonged"
    end
  end

  -- Set the amz headers (Remove .ARTIFACTS_BEFORE/[d]+/ from source, if needed)
  --
  if ngx.var.encoded_key:match("^[^/]+/%.ARTIFACTS_BEFORE/[0-9]+/") and build_src == build_tgt then
    ngx.var.x_amz_copy_source = "/" .. aws_src_bucket .. "/" .. ngx.var.encoded_key:gsub('^[^/]+/[^/]+/[^/]+/', build_src .. "/", 1)
  else
    ngx.var.x_amz_copy_source = "/" .. aws_src_bucket .. "/" .. ngx.var.encoded_key:gsub('^[^/]+/', build_src .. "/", 1)
  end

  -- Compute signature.
  --
  compute_S3_signature ("x-amz-copy-source:" .. ngx.var.x_amz_copy_source .. "\nx-amz-date:" .. ngx.var.x_amz_date)

elseif signature_mode == "PRESIGN" then

  -- PRESIGN mode.
  --

  local build_tgt, expires

  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  build_tgt = ngx.var.canonical_path:match("^[^/]+")

  -- Set the target bucket.
  --
  scan_tgt_buckets(build_tgt)

  -- Set presignature expiration
  --
  expires = ngx.time() + 3600

  -- Compute presignature.
  --
  compute_S3_presignature (expires)

  -- Redirect directly from here.
  --
  return ngx.redirect(ngx.var.redirect_endpoint .. "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key .. "?" .. ngx.var.presign_query_string, ngx.HTTP_MOVED_TEMPORARILY);

elseif signature_mode == "MULTIPART_INITIATE" then

  -- MULTIPART_INITIATE: POST /{key}?uploads
  -- Initiates a multipart upload; S3 returns an uploadId.
  --
  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  if ngx.var.aws_tgt_bucket == "" then
    ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
  end
  ngx.var.x_amz_acl = "private"
  compute_S3_signature_with_resource(
    "x-amz-acl:" .. ngx.var.x_amz_acl .. "\nx-amz-date:" .. ngx.var.x_amz_date,
    "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key .. "?uploads"
  )

elseif signature_mode == "MULTIPART_UPLOAD_PART" then

  -- MULTIPART_UPLOAD_PART: PUT /{key}?partNumber=N&uploadId=X
  -- Uploads one chunk; S3 returns an ETag for the part.
  -- partNumber < uploadId alphabetically → correct V2 sort order.
  --
  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  if ngx.var.aws_tgt_bucket == "" then
    ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
  end
  local part_number = ngx.var.arg_partNumber or ""
  local upload_id   = ngx.var.arg_uploadId   or ""
  compute_S3_signature_with_resource(
    "x-amz-date:" .. ngx.var.x_amz_date,
    "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key .. "?partNumber=" .. part_number .. "&uploadId=" .. upload_id
  )

elseif signature_mode == "MULTIPART_COMPLETE" then

  -- MULTIPART_COMPLETE: POST /{key}?uploadId=X
  -- Sends XML body with part ETags; S3 assembles the final object.
  --
  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  if ngx.var.aws_tgt_bucket == "" then
    ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
  end
  local upload_id = ngx.var.arg_uploadId or ""
  compute_S3_signature_with_resource(
    "x-amz-date:" .. ngx.var.x_amz_date,
    "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key .. "?uploadId=" .. upload_id
  )

elseif signature_mode == "MULTIPART_ABORT" then

  -- MULTIPART_ABORT: DELETE /{key}?uploadId=X
  -- Cancels an in-progress multipart upload and frees stored parts.
  --
  ngx.var.encoded_key = get_encoded_key(ngx.var.canonical_path)
  if ngx.var.aws_tgt_bucket == "" then
    ngx.var.aws_tgt_bucket = aws_bucket_prefix .. "-staging"
  end
  local upload_id = ngx.var.arg_uploadId or ""
  compute_S3_signature_with_resource(
    "x-amz-date:" .. ngx.var.x_amz_date,
    "/" .. ngx.var.aws_tgt_bucket .. "/" .. ngx.var.encoded_key .. "?uploadId=" .. upload_id
  )

else

  --
  -- Unkown signature mode.
  --
  ngx.log(ngx.ERR, "unknown signature_mode")
  ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)

end
