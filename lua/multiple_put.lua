-- Grab src and tgt builds.
--

local build_src = string.match(ngx.var.canonical_path, "^([^/]+)/")

local url, res

local body = ngx.var.request_body

url = "/force_real_request/upload_raw/" .. build_src .. "/.final_status"
res = ngx.location.capture(url, { method = ngx.HTTP_PUT, body = ngx.var.request_body })
--if res.status == 200 then
--  ngx.say('DONE')
--  ngx.flush(true)
--end

url = "/force_real_request/upload_raw/" .. build_src .. "/.blablabla"
res = ngx.location.capture(url, { method = ngx.HTTP_PUT, body = ngx.var.request_body })
--if res.status == 200 then
--  ngx.say('DONE')
--  ngx.flush(true)
--end

ngx.exit(ngx.HTTP_OK)
