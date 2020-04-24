-- ngx.say("extra path infos: " .. ngx.var.canonical_path)

function error(code, msg)
  ngx.status = code
  ngx.say(msg)
  ngx.exit(ngx.OK)
end

function read_body_args(body_content)
  local line
  local branch=nil
  local status=nil
  for line in body_content:gmatch("[^\n\r]+") do
    local vars, err = line:gmatch("(.*)=(.*)")
    if not vars then
      error(442, "Invalid body line: " .. line .. "Error: " .. err)
    end
    for k, v in vars do
      if k == "branch" then
        branch = v
      elseif k == "status" then
        status = v
      else
        error(443, "Invalid key in body: " .. k)
      end
    end
  end
  return branch, status
end

function check_body_args(branch, status)
  if not branch then
    error(444, "Branch not set in body")
  end
  if not status then
    error(444, "Status not set in body")
  elseif status ~= "SUCCESSFUL" and status ~= "FAILED" then
    error(444, "Invalid status content: " .. status)
  end
end


ngx.req.read_body()
branch, status = read_body_args(ngx.var.request_body)
check_body_args(branch, status)

ngx.say("branch: " .. branch.. ", status: " .. status .. "\n")


local base_url = "/force_real_request/upload_raw/extra/"
local url = base_url .. ""
--local res = ngx.location.capture(url)
--local body = res.body
-- ngx.say("sub request:")
-- ngx.say(body)





--/extra/commit/$repo_name/$stage_name/$commit_name/$artifacts_name/.final_status (for commit search)
--/extra/branch/$repo_name/$stage_name/$branch_name/$artifacts_name/.final_status (for branch search)
--
-- repo_name can be “bitbucket/scality/ring”
--  stage_name can be “pre-merge”
--  commit_name can be “1009bdd”




--Query: (pas ici)
--  /latest/(branch|commit)/stage_value/(branch_value|commit_value)/
--  /last_success/(branch|commit)/stage_value/(branch_value|commit_value)/
--  /last_failure/(branch|commit)/stage_value/(branch_value|commit_value)/


-- fetch /extra/commit
-- fetch /extra/branch


