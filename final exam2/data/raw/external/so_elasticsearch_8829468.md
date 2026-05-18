# Elasticsearch query to return all records

- 来源: Stack Overflow
- 问题ID: 8829468
- 标签: database, elasticsearch, query-string, elasticsearch-dsl
- 得分: 637
- 回答数: 29
- 抓取时间(UTC): 2026-05-18T09:34:41.329581+00:00
- 原始链接: https://stackoverflow.com/questions/8829468/elasticsearch-query-to-return-all-records

## 问题

I have a small database in Elasticsearch and for testing purposes would like to pull all records back. I am attempting to use a URL of the form... ``` `http://localhost:9200/foo/_search?pretty=true&q={'matchAll':{''}} ` ``` Can someone give me the URL you would use to accomplish this, please?

## 最佳回答

I think lucene syntax is supported so: `http://localhost:9200/foo/_search?pretty=true&q=*:*` size defaults to 10, so you may also need `&size=BIGNUMBER` to get more than 10 items. (where BIGNUMBER equals a number you believe is bigger than your dataset) BUT, elasticsearch documentation suggests for large result sets, using the scan search type. EG: ``` `curl -XGET 'localhost:9200/foo/_search?search_type=scan&scroll=10m&size=50' -d ' { "query" : { "match_all" : {} } }' ` ``` and then keep requesting as per the documentation link above suggests. EDIT: `scan` Deprecated in 2.1.0. `scan` does not provide any benefits over a regular `scroll` request sorted by `_doc`. link to elastic docs (spotted by @christophe-roussy)
