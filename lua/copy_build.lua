-- Grab src and tgt builds.
--

local build_src, build_tgt = string.match(ngx.var.canonical_path, "([^/]+)/([^/]+)/")

local url, res

-- Check if .final_status is present on build_src.
--
url = "/force_real_request/download/" .. build_src .. "/.final_status"
res = ngx.location.capture(url)
if res.status ~= 200 then
  ngx.say('SOURCE BUILD NOT FINISHED (NO ".final_status" FOUND), ABORTING')
  return
end

-- Check that build_tgt is empty
--
ngx.say("Checking if the target reference '" .. build_tgt .. "' is empty")
ngx.flush(true)
url = "/force_real_request/download/" .. build_tgt .. "/?format=txt"
res = ngx.location.capture(url)
if res.body == "" and res.truncated == false then
  ngx.say('DONE')
  ngx.flush(true)
else
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

-- Add a reference to the original build, if needed.
--
ngx.say("Adding the source reference '" .. build_src .. "' if needed")
ngx.flush(true)
url = "/force_real_request/download/" .. build_src .. "/.original_build"
res = ngx.location.capture(url)
if res.status == 200 then
  ngx.say('DONE')
  ngx.flush(true)
else
  url = "/force_real_request/upload/" .. build_src .. "/.original_build"
  res = ngx.location.capture(url, { method = ngx.HTTP_PUT, body = build_src })
  if res.status == 200 then
    ngx.say('DONE')
    ngx.flush(true)
  else
    ngx.say('FAILED')
    ngx.flush(true)
    return
  end
end

-- Process each object listed in build_src.
--
ngx.say("Listing objects from the source reference '" .. build_src .. "'")
url = "/force_real_request/download/" .. build_src .. "/?format=txt"
res = ngx.location.capture(url)
if res.status == 200 and res.truncated == false then
  ngx.say('DONE')
  ngx.flush(true)
else
  ngx.say('FAILED')
  ngx.flush(true)
  return
end

local objects = {}
for object in res.body:gmatch("([^\r\n]+)[\r\n]+") do
  table.insert(objects, object)
end

-- Multipart copy: copy a single object using S3 UploadPartCopy.
-- Used as a fallback when CopyObject returns EntityTooLarge (file > 5 GB on
-- Scaleway) or when COPY_OBJECT_SIZE_LIMIT forces the path for testing.
--
local function multipart_copy(object, file_size_hint)
  local file_size = file_size_hint
  if not file_size then
    local head_res = ngx.location.capture(
      "/force_real_request/download/" .. build_src .. "/" .. object,
      { method = ngx.HTTP_HEAD }
    )
    if head_res.status ~= 200 then
      return false, "HEAD failed: " .. head_res.status
    end
    file_size = tonumber(head_res.header["Content-Length"])
    if not file_size then
      return false, "no Content-Length header"
    end
  end

  -- Scaleway limits multipart uploads to 1,000 parts; AWS S3 minimum part size
  -- is 5 MB.  Choose the larger of the two so we never exceed 1,000 parts.
  local min_part_size = 5 * 1024 * 1024
  local max_parts     = 1000
  local part_size     = math.max(min_part_size, math.ceil(file_size / max_parts))
  local num_parts     = math.max(1, math.ceil(file_size / part_size))

  -- Initiate multipart upload on the target.
  local initiate_res = ngx.location.capture(
    "/force_real_request/copy-multipart-initiate/" .. build_src .. "/" .. build_tgt .. "/" .. object,
    { method = ngx.HTTP_POST, body = "" }
  )
  if initiate_res.status ~= 200 then
    return false, "initiate failed: " .. initiate_res.status
  end
  local upload_id = initiate_res.body:match("<UploadId>([^<]+)</UploadId>")
  if not upload_id then
    return false, "no UploadId in initiate response"
  end

  -- Copy parts in batches of 16 (concurrent via capture_multi).
  local etags = {}
  local part_batch_size = 16
  for batch_start = 1, num_parts, part_batch_size do
    local batch_end = math.min(batch_start + part_batch_size - 1, num_parts)
    local part_reqs = {}
    for part_num = batch_start, batch_end do
      local byte_start = (part_num - 1) * part_size
      local byte_end   = math.min(byte_start + part_size - 1, file_size - 1)
      table.insert(part_reqs, {
        "/force_real_request/copy-multipart-part/" .. build_src .. "/" .. build_tgt .. "/" .. object ..
          "?partNumber=" .. part_num ..
          "&uploadId=" .. ngx.escape_uri(upload_id) ..
          "&copySourceRange=" .. ngx.escape_uri("bytes=" .. byte_start .. "-" .. byte_end),
        { method = ngx.HTTP_PUT, body = "" }
      })
    end

    local part_results = { ngx.location.capture_multi(part_reqs) }
    for i, part_res in ipairs(part_results) do
      local part_num = batch_start + i - 1
      if part_res.status ~= 200 then
        ngx.location.capture(
          "/force_real_request/copy-multipart-abort/" .. build_src .. "/" .. build_tgt .. "/" .. object ..
            "?uploadId=" .. ngx.escape_uri(upload_id),
          { method = ngx.HTTP_DELETE }
        )
        return false, "part " .. part_num .. " failed: " .. part_res.status
      end
      local etag = part_res.body:match("<ETag>([^<]+)</ETag>")
      if not etag then
        ngx.location.capture(
          "/force_real_request/copy-multipart-abort/" .. build_src .. "/" .. build_tgt .. "/" .. object ..
            "?uploadId=" .. ngx.escape_uri(upload_id),
          { method = ngx.HTTP_DELETE }
        )
        return false, "part " .. part_num .. ": no ETag in response"
      end
      etags[part_num] = etag
    end
  end

  -- Complete the multipart upload with the collected ETags.
  local xml_parts = {}
  for part_num = 1, num_parts do
    table.insert(xml_parts,
      "<Part><PartNumber>" .. part_num .. "</PartNumber>" ..
      "<ETag>" .. etags[part_num] .. "</ETag></Part>"
    )
  end
  local complete_xml = "<CompleteMultipartUpload>" .. table.concat(xml_parts) .. "</CompleteMultipartUpload>"

  local complete_res = ngx.location.capture(
    "/force_real_request/copy-multipart-complete/" .. build_src .. "/" .. build_tgt .. "/" .. object ..
      "?uploadId=" .. ngx.escape_uri(upload_id),
    { method = ngx.HTTP_POST, body = complete_xml }
  )
  if complete_res.status ~= 200 or complete_res.body:find("<Error>", 1, true) then
    ngx.location.capture(
      "/force_real_request/copy-multipart-abort/" .. build_src .. "/" .. build_tgt .. "/" .. object ..
        "?uploadId=" .. ngx.escape_uri(upload_id),
      { method = ngx.HTTP_DELETE }
    )
    return false, "complete failed: " .. complete_res.status
  end

  return true
end

local total_number_of_objects = #objects
local batch_size = 16
local current_object = 0

-- When COPY_OBJECT_SIZE_LIMIT is set, HEAD each file first and route files
-- larger than the threshold directly to multipart copy.  Used in tests to
-- exercise the multipart code path without needing actual >5 GB files.
-- In production the variable is unset: attempt CopyObject first and only fall
-- back to multipart when the backend returns EntityTooLarge.
--
local copy_size_limit = tonumber(os.getenv("COPY_OBJECT_SIZE_LIMIT"))

if copy_size_limit then

  -- Test/threshold mode: HEAD each batch then choose per-file.
  for batch_start = 1, total_number_of_objects, batch_size do
    local batch_end = math.min(batch_start + batch_size - 1, total_number_of_objects)

    local head_reqs = {}
    for i = batch_start, batch_end do
      table.insert(head_reqs, {
        "/force_real_request/download/" .. build_src .. "/" .. objects[i],
        { method = ngx.HTTP_HEAD }
      })
    end
    local head_results = { ngx.location.capture_multi(head_reqs) }

    for i, head_res in ipairs(head_results) do
      current_object = current_object + 1
      local object    = objects[batch_start + i - 1]
      local file_size = tonumber(head_res.header["Content-Length"]) or 0
      ngx.say("[" .. current_object .. "/" .. total_number_of_objects .. "] " .. object .. " ... ")
      if file_size > copy_size_limit then
        local ok, err = multipart_copy(object, file_size)
        if ok then
          ngx.say('DONE (multipart copy)')
        else
          ngx.say('FAILED: ' .. (err or 'unknown'))
          ngx.flush(true)
          return
        end
      else
        local copy_res = ngx.location.capture(
          "/force_real_request/copy/" .. build_src .. "/" .. build_tgt .. "/" .. object,
          { method = ngx.HTTP_PUT, body = "" }
        )
        if copy_res.status == 200 then
          ngx.say('DONE')
        else
          ngx.say('FAILED')
          ngx.flush(true)
          return
        end
      end
    end
    ngx.flush(true)
  end

else

  -- Production mode: CopyObject batch, fall back to multipart on EntityTooLarge.
  for batch_start = 1, total_number_of_objects, batch_size do
    local batch_end = math.min(batch_start + batch_size - 1, total_number_of_objects)
    local urls = {}
    for i = batch_start, batch_end do
      table.insert(urls, {
        "/force_real_request/copy/" .. build_src .. "/" .. build_tgt .. "/" .. objects[i],
        { method = ngx.HTTP_PUT, body = '' }
      })
    end

    local results = { ngx.location.capture_multi(urls) }

    for i, object_res in ipairs(results) do
      current_object = current_object + 1
      local object = objects[batch_start + i - 1]
      ngx.say("[" .. current_object .. "/" .. total_number_of_objects .. "] " .. object .. " ... ")
      if object_res.status == 200 then
        ngx.say('DONE')
      elseif object_res.status == 400 and object_res.body:find("EntityTooLarge", 1, true) then
        ngx.say("large file, switching to multipart copy")
        ngx.flush(true)
        local ok, err = multipart_copy(object)
        if ok then
          ngx.say('DONE')
        else
          ngx.say('FAILED: ' .. (err or 'unknown'))
          ngx.flush(true)
          return
        end
      else
        ngx.say('FAILED')
        ngx.flush(true)
        return
      end
    end
    ngx.flush(true)
  end

end

ngx.say("BUILD COPIED")
