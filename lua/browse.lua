--
--
-- Browse through the three storage buckets transparently
--
--

local aws_bucket_prefix = os.getenv('AWS_BUCKET_PREFIX')


-- Check if this is a promoted build.
--
local function is_promoted(build_name)
  if build_name:match("^[a-z]+:[a-z]+:[%-A-Za-z0-9]+:promoted-") then
    return true
  end
  return false
end


-- Check if this is a staging build (with no expiration disabled).
--
local function is_staging (build_name)
  if build_name:match("^[a-z]+:[a-z]+:[%-A-Za-z0-9]+:staging-") then
    return true
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


-- Get entries from a list of buckets in parallel.
--
local function get_lists(delimiter, buckets)
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
local function render_header(mode)
  if mode == "html" then
    local fileContent = read_file("/etc/nginx/browse_header.html")
    ngx.print(fileContent)
  end
end


-- Send the entries in the appropriate format.
--
local function render_list(mode, entries, buckets)
  for i = 1, #buckets do
    local bucket_entries = entries[buckets[i]]
    local output = ""
    if mode == "html" and #buckets > 1 then
      output = output .. "<hr>" .. buckets[i] .. "</hr>\n"
    end
    for j = 1, #bucket_entries do
      local object = bucket_entries[j]
      if mode == "html" then
        output = output .. "<li class='list-group-item'><span class='glyphicon glyphicon-folder-open' aria-hidden='true'>&nbsp;</span><a href ='./" .. object .. "'>" .. object .. "</a></li>\n"
      else
        output = output .. object .. "\n"
      end
    end
    ngx.print(output)
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
if ngx.var.arg_format == nil or ngx.var.arg_format == "" or ngx.var.arg_format == "html" then
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

entries = get_lists(delimiter, buckets)

-- Tweak the response header.
--
set_content_type(browse_mode)


-- Send the response body.
--
render_header(browse_mode)
render_list(browse_mode, entries, buckets)
render_footer(browse_mode)
