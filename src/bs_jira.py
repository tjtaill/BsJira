from jira.client import JIRA
from jira_issue_formatters import IssueTabulator

class Issue(object):
    """
    This is wrapper class for jir issues
    so that the same issue returns the same hash
    and is equal regardless of memory address
    """
    def __init__(self, jira_issue):
        self.jira_issue = jira_issue
    
    def __getattr__(self, attrname):
        """
        dispatch all unknown property lookups to the wrapped
        jira class, I love python auto delegation
        """
        return getattr(self.jira_issue.fields, attrname)
    
    def __hash__(self, *args, **kwargs):
        return hash(str(self.jira_issue))
        
    def __eq__(self, other):
        return str(self.jira_issue) == str(other.jira_issue)
    
    def __str__(self):
        return str(self.jira_issue)
    
    def __repr__(self):
        repr(self.jira_issue)
    
    
class JqlIssueQuery(object):
    """
    This class is used to build jql query strings
    using the builder pattern
    """
    def _build_translations(self):
        jql_translations = {}
        jql_translations['is'] = '='
        jql_translations['isnot'] = '!='
        jql_translations['equal'] = '='
        jql_translations['equalto'] = '='
        jql_translations['greater'] = '>'
        jql_translations['greaterthan'] = '>'
        jql_translations['greaterEqual'] = '>='
        jql_translations['less'] = '<'
        jql_translations['lessThan'] = '<'
        jql_translations['lessEqual'] = '<'
        jql_translations['than'] = ''
        jql_translations['openParen'] = '('
        jql_translations['closeParen'] = ')'
        return jql_translations
    
    def __init__(self):
        self.jql_fragments = []
        """
        last = len(projects) - 1
        for i, project in enumerate(projects):
            self.jql_fragments.append('project=%s' % project)
            if i < last:
                self.jql_fragments.append(' or ')
        self.jql_fragments.append(' and')
        """
        self.translate = self._build_translations()
        
    def clear(self):
        self.jql_fragments = []
        return self
    
    def build(self):
        query = ''.join(self.jql_fragments)
        print(query) 
        return query
    
    def __getattr__(self, methodname):
        fragments = methodname.split('_')
        for fragment in fragments:
            if fragment == '':
                continue
            fragment = fragment if fragment not in self.translate else self.translate[fragment]
            self.jql_fragments.append( ' ' )
            self.jql_fragments.append( fragment )

            def method(arg):
                    if arg == '':
                        return self
                    self.jql_fragments.append(' ')
                    self.jql_fragments.append(arg)
                    return self
        return method   
        

class BsIssues(object):
    """
    A class meant to query issues from the me jira
    this class meant to be inherited from where the sub classes set the jira
    project example MAYA MayaIssues or MAX MaxIssues
    """
    def __init__(self, user, passwd):
        # sub classes should set the project appropriately MAYA, MAX. etc
        # after calling the parent constructor
        self.jira = \
            JIRA(options={'server': 'https://jira.broadsoft.com'}, basic_auth=(user, passwd))
        self.MAX_RESULTS = 500
        
    def query(self, jql):
        """
        helper method to abstract jira query logic
        all queries return a set of issues
        using set to allow complex query by using set operations like union, intersection and difference
        """
        return set([Issue(issue) for issue in 
                    self.jira.search_issues(jql, maxResults=self.MAX_RESULTS)] )
        
    def _add_users_to(self, jql, jira_user_ids):
        jql.and_('')
        jql.openParen('')
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            jql.assignee_is(jira_user_id)
            if i < last:
                """ python keyword or so use OR jql won't care """
                jql.or_('')
        jql.closeParen('')
    def open_assigned_to(self, jira_user_ids):
        """
        returns a set of issues that a list of jira user have yet to start
        """
        jql = JqlIssueQuery()
        jql.status_isnot('closed')
        self._add_users_to(jql, jira_user_ids)
        return self.query(jql.build())     
        
    def in_progress_by(self, jira_user_ids):
        """
        returns a set of issues that are in progress by a list of users
        """
        jql = JqlIssueQuery()
        jql.status_is("'In Progress'")
        self._add_users_to(jql, jira_user_ids)
        return self.query(jql.build())

    def _add_resolved_by_user(self, jql, jira_user_ids):
        last = len(jira_user_ids) - 1
        jql.openParen('')
        for i, jira_user_id in enumerate(jira_user_ids):
            jql.openParen('')
            jql.resolution_changed_to('Fixed').by(jira_user_id)
            jql.or_resolution_changed_to('"By Design"').by(jira_user_id)
            jql.or_status_changed_to('Closed').by(jira_user_id)
            jql.closeParen('')
            if i < last:
                jql.or_('')
        jql.closeParen('')
    
    def resolved_in(self, jira_user_ids, fix_versions):
        """
        returns a set of closed issues by users and fix verions( Iterations, PRs and Quarters)
        """
        jql = JqlIssueQuery()
        
        self._add_resolved_by_user(jql, jira_user_ids)
        
        last = len(fix_versions) - 1
        jql.and_('')
        for i, fix_version in enumerate(fix_versions):
            jql.fixVersion_is(fix_version)
            if i < last:
                jql.or_('')
        
        return self.query(jql.build())
    
    def resolved_between(self, jira_user_ids, from_date, to_date):
        """
        date format is YYYY/MM/DD example 2014/05/03 May 3, 2014
        also need to double quote dates '"2014/05/03"'
        """
        jql = JqlIssueQuery()
        self._add_resolved_by_user(jql, jira_user_ids)        
        jql.and_resolutiondate_greaterEqual(from_date)
        jql.and_resolutiondate_lessThan(to_date)
        return self.query(jql.build())
    
    def recently_resolved(self, jira_user_ids, days_ago):
        """
        date format is YYYY/MM/DD example 2014/05/03 May 3, 2014
        also need to double quote dates '"2014/05/03"'
        """
        jql = JqlIssueQuery()
        self._add_resolved_by_user(jql, jira_user_ids)        
        resolved_days_ago = ''.join( ['resolved', ' ', '>=', ' ', '-', str(days_ago), 'd'])
        jql.and_(resolved_days_ago)
        return self.query(jql.build())

    def _add_user_woked_on_last_week(self, jql, jira_user_id):
        jql.openParen_openParen_status_changed_to("'In Progress'")
        jql.by(jira_user_id)
        jql.after('startOfWeek(-1)')
        jql.before('startOfWeek()')        
        jql.closeParen('')
        jql.or_openParen_resolution_changed_to('Fixed')
        jql.by(jira_user_id)
        jql.after('startOfWeek(-1)')
        jql.before('startOfWeek()')
        jql.closeParen('')        
        jql.or_openParen_resolution_changed_to('"By Design"')
        jql.by(jira_user_id)
        jql.after('startOfWeek(-1)')
        jql.before('startOfWeek()')
        jql.closeParen('')
        jql.closeParen('')        
        
    def _add_user_resolved_last_week(self, jql, jira_user_id):
        jql.openParen_openParen_resolution_changed_to('Fixed')
        jql.by(jira_user_id)
        jql.after('startOfWeek(-1)')
        jql.before('startOfWeek()')
        jql.closeParen('')
        jql.or_openParen_resolution_changed_to('"By Design"')
        jql.by(jira_user_id)
        jql.after('startOfWeek(-1)')
        jql.before('startOfWeek()')
        jql.closeParen_closeParen('')        
        
    def _add_user_resolved_this_week(self, jql, jira_user_id):
        jql.openParen_openParen_resolution_changed_to('Fixed')
        jql.by(jira_user_id)
        jql.after('startOfWeek()')
        jql.before('endOfWeek()')
        jql.closeParen('')
        jql.or_openParen_resolution_changed_to('"By Design"')
        jql.by(jira_user_id)
        jql.after('startOfWeek()')
        jql.before('endOfWeek()')
        jql.closeParen_closeParen('')

    def _add_progressed_last_week(self, jql, jira_user_id):
        jql.openParen_openParen_status_changed_by(jira_user_id)
        jql._and_status_changed_after('-1w')
        jql.closeParen_closeParen('')

    def _add_progressed_last_year(self, jql, jira_user_id):
        jql.openParen_openParen_status_changed_by(jira_user_id)
        jql._and_status_changed_after('-364d')
        jql.closeParen_closeParen('')

    def worked_on_last_week_by(self, jira_user_ids):
        jql = JqlIssueQuery()
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            self._add_user_woked_on_last_week(jql, jira_user_id)
            if i < last:
                jql.or_('')
        return self.query(jql.build())

    def progressed_last_week(self, jira_user_ids):
        jql = JqlIssueQuery()
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            self._add_progressed_last_week(jql, jira_user_id)
            if i < last:
                jql.or_('')
        return self.query(jql.build())

    def progressed_last_year(self, jira_user_ids):
        jql = JqlIssueQuery()
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            self._add_progressed_last_year(jql, jira_user_id)
            if i < last:
                jql.or_('')
        return self.query(jql.build())

    def resolved_last_week(self, jira_user_ids):
        jql = JqlIssueQuery()
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            self._add_user_resolved_last_week(jql, jira_user_id)
            if i < last:
                jql.or_('')
        return self.query(jql.build())
    
    def resolved_last_year(self, jira_user_ids, component):
        jql = JqlIssueQuery()
        self._add_resolved_by_user(jql, jira_user_ids)
        resolved_a_year_ago = ''.join( ['resolved', ' >=', ' -400d'])
        jql.and_(resolved_a_year_ago)
        jql.and_component_is(component)
        return self.query(jql.build())

    def resolved_this_week(self, jira_user_ids):
        jql = JqlIssueQuery()
        last = len(jira_user_ids) - 1
        for i, jira_user_id in enumerate(jira_user_ids):
            self._add_user_resolved_this_week(jql, jira_user_id)
            if i < last:
                jql.or_('')
        return self.query(jql.build())
    
    def recently_fixed_in(self, components, days_ago):
        jql = JqlIssueQuery()
        jql.issuetype_is('Defect')
        jql.and_status_is('Closed')
        last = len(components) - 1
        jql.and_('')
        for i, component in enumerate(components):
            jql.component_is(component)
            if i < last:
                jql.or_('')
        resolved_days_ago = ''.join( ['resolved', ' >=', ' -', str(days_ago), 'd'])
        jql.and_(resolved_days_ago)
        return self.query(jql.build())    
    
    def defects_in(self, components):
        """
        returns a set of open defect issues
        components a list of components Example ['Foundation', "'Multiple Representation'"]
        """
        jql = JqlIssueQuery()
        jql.issuetype_is('Defect')
        jql.and_status_is('Open')
        last = len(components) - 1
        jql.and_('')
        for i, component in enumerate(components):
            jql.component_is(component)
            if i < last:
                jql.or_('')
        return self.query(jql.build())

    def _jiras_from_links(self, issue):
        links = getattr(issue, 'issuelinks')
        jiras = set()
        for link in links:
            if not hasattr(link, 'outwardIssue'):
                continue
            jiras.add(str(link.outwardIssue))
        return jiras
    
    def linked_to(self, assignees, links):
        unfiltered_issues = self.open_assigned_to(assignees)
        filtered_issues = []
        for issue in unfiltered_issues:
            jiras = self._jiras_from_links(issue)
            if jiras & links:
                filtered_issues.append(issue)
        return filtered_issues


if __name__ == '__main__':
    from getpass import getpass

    passwd = getpass()

    bsIssues = BsIssues('ttaillefer', passwd)

    me = ['ttaillefer']
    team = ['nicolas', 'ttaillefer', 'mreiher-chancy', 'mpiotte', 'scossette', 'ist-andre', 'oforrest', 'ablais', 'ejulien']

    """
    members = ['ttaillefer', 'mreiher-chancy']
    for member in members:
        results = mayaIssues.resolved_this_week([member])
        print('%s:%d' % (member, len(results)))
    
    """
    # results = mayaIssues.worked_on_last_week_by(['taillet'])
    # results = mayaIssues.recently_fixed(['"File Referencing"'], 180)
    # results = mayaIssues.in_progress_by(['larochs'])
    # results = mayaIssues.recently_resolved(['taillet'], 8)    
    # results = mayaIssues.resolved_last_year(['taillet'], '"Multiple Representation"')
    # results = mayaIssues.defects_in(['"Multiple Representation"'])
    # teamIssues = bsIssues.open_assigned_to(team)
    # teamIssues = bsIssues.progressed_last_year(me)
    # issue_tabulator = IssueTabulator(bsIssues.jira)
    # print(issue_tabulator.tabulate(teamIssues, ['id', 'summary', 'status']))
    """
    for team_member in team:
        with open(team_member + '.txt', 'w') as f:
            issues = bsIssues.progressed_last_year([team_member])
            issue_tabulator = IssueTabulator(bsIssues.jira)
            f.write(issue_tabulator.tabulate(issues, ['id', 'summary', 'status']))
    """
    # issues = bsIssues.progressed_last_week(me)
    issues = bsIssues.linked_to(['ttaillefer', 'ejulien', 'scossette'], {'BW-8290'})
    issue_tabulator = IssueTabulator(bsIssues.jira)
    print(issue_tabulator.tabulate(issues, ['id', 'summary', 'status', 'assignee', 'issuelinks']))


