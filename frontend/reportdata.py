from __future__ import print_function
'''
Created on Feb 1, 2012

@author: jmussler
'''

import DataDB
import psycopg2
import psycopg2.extras
from collections import defaultdict
import hosts
import datetime

#@funccache.lru_cache(60,25)
def getLoadReportData():
    conn = DataDB.getDataConnection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    query = """
            with q as (
                select 
                  t_host_id
                , week
                , (select round((sum(tsd_table_size) + sum(tsd_table_size))/10^9::numeric,1)::text
                     from monitor_data.table_size_data
                    where tsd_timestamp = max) as db_size 
                from (
                    select
                        t_host_id
                      , extract(week from tsd_timestamp) as week               
                      , max(tsd_timestamp)
                    from  monitor_data.table_size_data
                        , monitor_data.tables
                    where tsd_timestamp > ('now'::timestamp - '9 weeks'::interval)
                    and tsd_table_id = t_id
                    group by t_host_id, extract(week from tsd_timestamp)
                ) a
            )
            select 
                  load_host_id AS id,
                  extract(week from load_timestamp)::text AS kw,
                  round(avg(load_1min_value)/100,2) AS avg,
                  round(max(load_1min_value)/100,2) AS max,
                  to_char(min(load_timestamp::date),'dd.mm.YYYY') AS min_date,
                  to_char(max(load_timestamp::date),'dd.mm.YYYY') AS max_date,
                  min(load_timestamp::date) AS sort_date,
                  max(q.db_size) as db_size
             from monitor_data.host_load
                , monitor_data.hosts
                , q
            where host_id = load_host_id
              and host_enabled
              and load_timestamp > ('now'::timestamp - '9 weeks'::interval)
              and extract(dow from load_timestamp) IN(1,2,3,4,5)                      
              and q.t_host_id = load_host_id
              and q.week = extract(week from load_timestamp)
            group by load_host_id, extract(week from load_timestamp)
            order by 1 ASC,7 DESC
            """
    cur.execute(query)

    data = defaultdict(list)

    lastRR = None

    for r in cur:

        rr = {'id' : r['id'],
              'avg' : r['avg'],
              'max' : r['max'],
              'min_date' : r['min_date'],
              'max_date' : r['max_date'],
              'db_size' : r['db_size'],
              'trendAvg': 0,
              'trendMax': 0,
              'kw' : r['kw']
              }

        if lastRR != None and lastRR['id']==rr['id']:
            if lastRR['max'] < r['max']:
                lastRR['trendMax'] = -1
            elif lastRR['max'] > r['max']:
                lastRR['trendMax'] = 1

            if lastRR['avg'] < r['avg']:
                lastRR['trendAvg'] = -1
            elif lastRR['avg'] > r['avg']:
                lastRR['trendAvg'] = 1

            if lastRR['db_size'] < r['db_size']:
                lastRR['trendSize'] = -1
            elif lastRR['db_size'] > r['db_size']:
                lastRR['trendSize'] = 1

        data[int(r['id'])].append(rr);
        lastRR = rr

    cur.close()
    conn.close()

    return sorted(data.values(), key = lambda x : hosts.hosts[x[0]['id']]['settings']['uiShortName'])


def getTablePerformanceIssues(hostname, date_from, date_to):
    conn = DataDB.getDataConnection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select * from monitor_data.get_table_threshold_sinners_for_period(%s,%s,%s)""", (hostname, date_from, date_to))
    data = [] # cur.fetchall()
    for r in cur:
        row = {'host_name' : r['host_name'],
              'host_id' : r['host_id'],
              'schema_name' : r['schema_name'],
              'table_name' : r['table_name'],
              'day' : r['day'],
              'scan_change_pct' : r['scan_change_pct'],
              'scans1': r['scans1'],
              'scans2': r['scans2'],
              'size1': r['size1'],
              'size2': r['size2'],
              'size_change_pct': r['size_change_pct'],
              'allowed_seq_scan_pct': r['allowed_seq_scan_pct'],
              }
        data.append(row)
    cur.close()
    conn.close()
    return data

def getApiPerformanceIssues(hostname, api_from, api_to):
    conn = DataDB.getDataConnection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""select * from monitor_data.get_sproc_threshold_sinners_for_release(%s,%s,%s)""", (hostname, api_from, api_to))
    data = [] # cur.fetchall()
    for r in cur:
        row = {'host_name' : r['host_name'],
              'host_id' : r['host_id'],
              'sproc_schema' : r['sproc_schema'],
              'sproc_name' : r['sproc_name'],
              'calltime_change_pct' : r['calltime_change_pct'],
              'share_on_total_runtime' : r['share_on_total_runtime'],
              'execution_avg1': r['execution_avg1'],
              'execution_avg2': r['execution_avg2'],
              'calls1': r['calls1'],
              'calls2': r['calls2'],
              'callscount_change_pct': r['callscount_change_pct'],
              'allowed_runtime_growth_pct': r['allowed_runtime_growth_pct'],
              'allowed_share_on_total_runtime_pct': r['allowed_share_on_total_runtime_pct'],
              }
        data.append(row)
    cur.close()
    conn.close()
    return data


if __name__ == '__main__':
    DataDB.setConnectionString("dbname=dbmonitor host=sqlwiki.db.zalando user=pgobserver_frontend_test password=ndowifwensa port=5433")
    #print (getTablePerformanceIssues('customer1.db.zalando',datetime.date(2013,8,23),datetime.date(2013,8,26)))
    print (getApiPerformanceIssues('stock2.db.zalando','r13_00_33','r13_00_34'))

