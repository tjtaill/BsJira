"""
This module is used to format jira issues
specifically 
from bs_jira import Issue
"""
from tabulate import tabulate
from collections import defaultdict
from textwrap import wrap
import datetime


class IssueTabulator(object):
    def _format(self, issue, field):
        attr = getattr(issue, field)
        # TODO : investigate unicode issues for python 3.0
        unwrapped = str(attr) 
        # self._strip_unicode(attr) if type(attr) is unicode else str(attr)
        wrapped = wrap( unwrapped, self._max_field_length, replace_whitespace=False)
        return wrapped
    
    def _strip_unicode(self, unicode_string):
        ascii_chars = []
        for char in unicode_string:
            if ord(char) > 128:
                continue
            ascii_chars.append(char)
        return ''.join(ascii_chars) 

    def _issue(self, issue, field):
        return [str(issue)]

    def _progress(self, issue, field):
        progress = getattr(issue, field)
        return 'unknown' if not hasattr(progress, 'percent') else ['%s %%' % str(progress.percent)] 

    def _time(self, issue, field):
        seconds = getattr(issue, field)
        return [str(0)] if not seconds else [str(datetime.timedelta(seconds=seconds))]
    
    def _worklogs(self, issue, field):
        woklogs = self.jira.worklogs(issue)
        acc = []
        for worklog in woklogs:
            if hasattr(worklog, 'raw') and 'comment' in worklog.raw:
                acc.append( self._strip_unicode(worklog.raw['comment']) )
                acc.append( '\n' )
        unwrapped = ''.join(acc)
        wrapped = wrap(unwrapped, self._max_field_length)            
        return wrapped
    
    def _comments(self, issue, field):
        comments = self.jira.comments(issue)
        acc = []
        for comment in comments:
            if hasattr(comment, 'body'):
                acc.append(self._strip_unicode(comment.body))
                acc.append('\n')                        
        unwrapped = ''.join(acc)
        wrapped = wrap(unwrapped, self._max_field_length)
        return wrapped
    
    def _build_formatters(self):
        formatters = defaultdict(lambda: self._format)
        formatters['id'] = self._issue
        formatters['aggregateprogress'] = self._progress
        formatters['progress'] = self._progress
        formatters['timespent'] = self._time
        formatters['aggregatetimeestimate'] = self._time 
        formatters['aggregatetimeoriginalestimate'] = self._time 
        formatters['aggregatetimespent'] = self._time
        formatters['timeestimate'] = self._time
        formatters['timeoriginalestimate'] = self._time
        formatters['worklog'] = self._worklogs
        formatters['comments'] = self._comments
        return formatters
    
    def _build_multiline(self):
        multiline = defaultdict(False)
        multiline['description'] = True
        return multiline
    
    def __init__(self, jira_connection, max_field_length=40):
        self.jira = jira_connection
        self.formatters = self._build_formatters()
        self._max_field_length = max_field_length
        
    def tabulate(self, issues, fields):
        formatters = self.formatters
        rows = [fields]
        for issue in issues:
            values = {}
            lengths = {}
            max_length = 0
            for field in fields:
                formatter = formatters[field]
                values[field] = formatter(issue, field)
                lengths[field] = len(values[field])
                max_length = max(max_length, lengths[field])            

            for i in range(max_length):
                row = []
                for field in fields:
                    if i < lengths[field]:
                        row.append(values[field][i])
                    else:
                        row.append("")
                rows.append(row)
        return tabulate(rows, headers='firstrow')
