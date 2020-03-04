--
--
-- Browse through the three storage buckets transparently
--
--

local aws_bucket_prefix = os.getenv('AWS_BUCKET_PREFIX')
local build_prefixes = { "dev%-", "preprod%-", "" }


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
  if is_promoted(build_tgt) then
    return aws_bucket_prefix .. "-promoted"
  elseif is_staging(build_tgt) then
    return aws_bucket_prefix .. "-staging"
  else
    return aws_bucket_prefix .. "-prolonged"
  end
end


-- Return the content of a file.
--
local function read_file(path)
    local file = io.open(path, "rb") -- r read mode and b binary mode

    if not file then
      return nil
    end

    local content = file:read "*a" -- *a or *all reads the whole file
    file:close()

    return content
end


-- Get entries from cache
--
local function get_lists_from_cache()
  cached_listing = read_file("/data/nginx/artifacts_full_listing_cache/listing")
  if cached_listing == nil then
    return nil
  end
  local prefix = ""
  if ngx.var.http_script_name ~= nil then
    prefix = string.match(ngx.var.http_script_name, "[^/]+/[^/]+/[^/]+/"):gsub("/", ":")
  end
  local entries = {}
  entries["cache_date"] = nil
  entries["cache"] = {}
  for object in cached_listing:gmatch("([^\r\n]+)[\r\n]+") do
    if entries["cache_date"] == nil then
      entries["cache_date"] = object
    elseif prefix == "" or object:sub(1, #prefix) == prefix then
      table.insert(entries["cache"], object)
    end
  end
  return entries
end


-- Get entries from a list of buckets in parallel.
--
local function get_lists_from_upstream(delimiter, buckets)
  local open_buckets = buckets

  local markers = {}
  local entries = {}
  for i=1, #buckets do
    markers[buckets[i]] = ""
    entries[buckets[i]] = {}
  end

  while #open_buckets > 0 do
    local urls = {}
    for i=1, #open_buckets do
      table.insert(urls, { "/force_real_request/browse_raw/" .. ngx.var.canonical_path .. "?delimiter=" .. delimiter .. "&marker=" .. markers[open_buckets[i]] .. "&bucket=" .. open_buckets[i] })
    end
    local next_buckets = {}
    local res = { ngx.location.capture_multi(urls) }
    for i=1, #res do
      if res[i].status == 200 then
        for object in res[i].body:gmatch("([^\r\n]+)[\r\n]+") do
          if object:sub(1,1) == '>' then
            table.insert(next_buckets, open_buckets[i])
	    markers[open_buckets[i]] = object:sub(2, #object)
            break
          end
          table.insert(entries[open_buckets[i]], object)
        end
      end
    end
    open_buckets = next_buckets
  end
  return entries
end


-- Set the appropriate Content-Type header.
--
local function set_content_type(mode)
  if mode == "html" then
    ngx.header["Content-Type"] = "text/html"
  else
    ngx.header["Content-Type"] = "text/plain"
  end
end


-- Send header if needed.
--
local function render_header(mode, cache_date)
  if mode == "html" then
    local fileContent = read_file("/etc/nginx/browse_header.html")
    ngx.print(fileContent)
    if cache_date ~= nil then
      ngx.print("<p align='right'><i>refreshed on " .. cache_date .. "&nbsp;&nbsp;</i></p>\n")
    end
  end
end


-- Send the entries in the appropriate format.
--
local function render_list(mode, entries, buckets)
  if mode == "html" then
    ngx.print("<ul class='list-group'>\n")
  end
  for i = 1, #buckets do
    local bucket_entries = entries[buckets[i]]
    for j = 1, #bucket_entries do
      local object = bucket_entries[j]
      if mode == "html" then
        rendered_object = ngx.escape_uri(object)
        rendered_object = rendered_object:gsub('%%2F', '/')
        ngx.print("<li class='list-group-item'><span class='glyphicon glyphicon-folder-open' aria-hidden='true'>&nbsp;</span><a href ='./" .. rendered_object .. "'>" .. object .. "</a></li>\n")
      else
	ngx.print(object .. "\n")
      end
    end
  end
  if mode == "html" then
    ngx.print("</ul>\n")
  end
end


-- Send footer if need.
--
local function render_footer(mode)
  if mode == "html" then
    local fileContent = read_file("/etc/nginx/browse_footer.html")
    ngx.print(fileContent)
  end
end


local browse_mode = ""
if ngx.var.canonical_path == "" and ngx.var.full_listing_mode == "UPSTREAM" then
  browse_mode = "text"
elseif ngx.var.arg_format == nil or ngx.var.arg_format == "" or ngx.var.arg_format == "html" then
  browse_mode = "html"
elseif ngx.var.arg_format == "text" then
  browse_mode = "text"
elseif ngx.var.arg_format == "txt" then
  browse_mode = "txt"
else
  ngx.exit(ngx.HTTP_BAD_REQUEST)
end


local delimiter = ""
if browse_mode == "html" or browse_mode == "text" then
  delimiter = "/"
elseif ngx.var.canonical_path == "" then
  -- no fulls scan from root dir
  --
  delimiter = "/"
end


-- if canonical_path is empty, put promoted, promoted, and staging in a list of buckets
-- otherwise put the guessed bucket in a list of buckets
-- 
local buckets = {}
local entries = {}
if ngx.var.arg_bucket ~= nil and ngx.var.arg_bucket ~= "" then
   buckets = { ngx.var.arg_bucket }
elseif ngx.var.canonical_path == "" then
  buckets = { aws_bucket_prefix .. "-promoted", aws_bucket_prefix .. "-prolonged", aws_bucket_prefix .. "-staging" }
else
  local build_tgt = string.match(ngx.var.canonical_path, "^([^/]+)/")
  local tgt_bucket = scan_tgt_buckets(build_tgt)
  buckets = { tgt_bucket }
end


-- Grab entries from upstream or cache
--
local cache_date = nil
if ngx.var.canonical_path == "" and ngx.var.full_listing_mode == "CACHE" and browse_mode == "html" then
  entries = get_lists_from_cache()
  if entries ~= nil then
    cache_date = entries["cache_date"]
    buckets = { "cache" }
  else
    entries = get_lists_from_upstream(delimiter, buckets)
  end
else
  entries = get_lists_from_upstream(delimiter, buckets)
end


-- Send HTTP 404 if needed, for browser only
--
if ngx.var.canonical_path ~= "" and #entries[buckets[1]] == 0 and browse_mode == "html" then
  ngx.exit(ngx.HTTP_NOT_FOUND)
end


-- Tweak the response header.
--
set_content_type(browse_mode)


-- Send the response body.
--
render_header(browse_mode, cache_date)
render_list(browse_mode, entries, buckets)
render_footer(browse_mode)
