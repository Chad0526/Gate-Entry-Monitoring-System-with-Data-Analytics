# Requirements Document: Guard Account Enhancements

## Introduction

This document specifies the requirements for enhancing the City College of Bayawan gate management system's guard account functionality. The enhancements provide guards with real-time notifications, expanded historical access, performance metrics, improved dashboard UI, comprehensive activity logging, and additional tools for shift handovers and visitor management. These improvements increase guard accountability, efficiency, and situational awareness while maintaining security boundaries and audit trail integrity.

## Glossary

- **Guard**: A user with the Guard role who operates the gate scanning system and monitors campus access
- **System**: The City College of Bayawan gate management web application
- **Dashboard**: The main guard interface displaying real-time statistics and quick actions
- **Notification_Service**: Component that creates and delivers alerts to guards
- **Activity_Logger**: Component that records all guard actions for audit purposes
- **History_Manager**: Component that provides access to historical gate entry data
- **Performance_Tracker**: Component that calculates guard-specific metrics
- **Scanner**: The QR code scanning interface for processing student entries
- **Shift**: A period of guard duty from clock-in to clock-out
- **Entry**: A gate scan record (GateEntry) representing a student entering or exiting campus
- **Incident**: A security event requiring guard attention (GateIncident)
- **Broadcast**: Sending a notification to all currently on-duty guards
- **On-Duty**: A guard with an active shift (shift_end is NULL)
- **Seven_Day_Window**: The last 7 days from today, inclusive
- **Admin**: A user with administrator privileges (unlimited access)
- **Supervisor**: A user with supervisor privileges (unlimited access)

## Requirements

### Requirement 1: Guard Notification System

**User Story:** As a guard, I want to receive real-time notifications about incidents, capacity alerts, and shift reminders, so that I can respond quickly to security events and stay informed during my shift.

#### Acceptance Criteria

1. WHEN an incident is reported with broadcast enabled, THE Notification_Service SHALL create a notification for each on-duty guard
2. WHEN an event reaches 80% capacity, THE Notification_Service SHALL create a capacity alert for all on-duty guards
3. WHEN a shift has 30 minutes remaining, THE Notification_Service SHALL create a shift reminder for the guard
4. WHEN a notification is created with priority 'urgent', THE System SHALL display it prominently in the dashboard
5. WHEN a guard views a notification, THE System SHALL mark it as read and update the read timestamp
6. WHEN a guard accesses the dashboard, THE System SHALL display the count of unread notifications in the navbar badge
7. WHEN no guards are on duty and a broadcast notification is requested, THE Notification_Service SHALL log a warning and continue operation
8. WHEN a notification has an expiration time, THE System SHALL not display it after the expiration timestamp

### Requirement 2: Expanded Historical Access

**User Story:** As a guard, I want to view gate entries from the last 7 days, so that I can review recent activity patterns and verify student entry history.

#### Acceptance Criteria

1. WHEN a guard requests entry history, THE History_Manager SHALL return entries from the last 7 days only
2. WHEN an admin or supervisor requests entry history, THE History_Manager SHALL return entries without date restrictions
3. WHEN a guard attempts to access entries older than 7 days, THE History_Manager SHALL automatically adjust the date range to the earliest allowed date
4. WHEN a date range is adjusted due to access restrictions, THE System SHALL display a warning message to the user
5. WHEN a guard filters entries by date range, THE System SHALL enforce the seven-day window constraint
6. WHEN a guard searches for a specific student, THE System SHALL return matching entries within the seven-day window
7. WHEN entry history is displayed, THE System SHALL show student name, ID, timestamp, scan type, and status
8. WHEN entry history exceeds 500 records, THE System SHALL limit results to 500 entries

### Requirement 3: Guard Performance Metrics

**User Story:** As a guard, I want to see my performance metrics including scans per hour and accuracy rate, so that I can track my efficiency and identify areas for improvement.

#### Acceptance Criteria

1. WHEN a guard views their performance metrics, THE Performance_Tracker SHALL calculate total scans for the specified period
2. WHEN calculating accuracy rate, THE Performance_Tracker SHALL divide successful scans by total scans
3. WHEN calculating scans per hour, THE Performance_Tracker SHALL divide total scans by total hours worked
4. WHEN a shift is ongoing, THE Performance_Tracker SHALL calculate metrics up to the current time
5. WHEN a guard has worked multiple shifts, THE Performance_Tracker SHALL aggregate statistics across all shifts in the period
6. THE Performance_Tracker SHALL ensure all calculated metrics are non-negative
7. THE Performance_Tracker SHALL ensure accuracy rate is between 0 and 100 percent
8. WHEN displaying performance metrics, THE System SHALL show total scans, successful scans, denied scans, accuracy rate, scans per hour, incidents reported, and overrides made

### Requirement 4: Real-Time Dashboard Updates

**User Story:** As a guard, I want my dashboard to automatically refresh with current statistics, so that I have up-to-date information without manually reloading the page.

#### Acceptance Criteria

1. WHEN a guard views the dashboard, THE System SHALL display the current count of students on campus
2. WHEN the dashboard is active, THE System SHALL automatically refresh statistics every 30 seconds
3. WHEN a guard has an active shift, THE Dashboard SHALL display shift duration, entries during shift, and entries by type
4. WHEN displaying hourly activity, THE Dashboard SHALL show entry counts for each hour of the current day
5. WHEN displaying recent activity, THE Dashboard SHALL show the last 20 gate entries with timestamp, student info, and status
6. WHEN active events exist, THE Dashboard SHALL display event name, venue, current attendees, capacity, and percentage
7. WHEN a guard has no active shift, THE Dashboard SHALL display a clock-in prompt
8. WHEN dashboard statistics are refreshed, THE System SHALL update the display without full page reload

### Requirement 5: Comprehensive Activity Logging

**User Story:** As a system administrator, I want all guard actions logged with detailed context, so that I can maintain a complete audit trail for accountability and compliance.

#### Acceptance Criteria

1. WHEN a guard scans a student QR code, THE Activity_Logger SHALL record the scan with guard ID, student ID, timestamp, device ID, and IP address
2. WHEN a guard overrides a scan decision, THE Activity_Logger SHALL record the override with the reason and original result
3. WHEN a guard reports an incident, THE Activity_Logger SHALL record the incident creation with all related details
4. WHEN a guard clocks in or out, THE Activity_Logger SHALL record the shift action with timestamp
5. WHEN a guard creates a note, THE Activity_Logger SHALL record the note creation with content and priority
6. WHEN a guard performs a student lookup, THE Activity_Logger SHALL record the search query and results count
7. THE Activity_Logger SHALL store additional context in the metadata JSON field
8. THE System SHALL prevent modification or deletion of activity log records after creation

### Requirement 6: Guard Notes and Shift Handover

**User Story:** As a guard, I want to create shift handover notes for the next guard, so that important information is communicated across shifts.

#### Acceptance Criteria

1. WHEN a guard creates a note, THE System SHALL associate it with the current shift if one is active
2. WHEN a note is created with 'urgent' priority, THE System SHALL send a notification to all on-duty guards
3. WHEN a guard views the dashboard, THE System SHALL display recent notes from previous shifts
4. WHEN a guard reads a note, THE System SHALL record the read action with timestamp
5. WHEN displaying notes, THE System SHALL show which guards have read each note
6. WHEN a guard searches notes, THE System SHALL filter by date range and priority
7. THE System SHALL allow notes to be created even when no shift is active
8. WHEN a note exceeds 2000 characters, THE System SHALL reject it with a validation error

### Requirement 7: Student Lookup and Verification

**User Story:** As a guard, I want to quickly look up student information and class schedules, so that I can verify identity and confirm students have class at the current time.

#### Acceptance Criteria

1. WHEN a guard searches by student ID, THE System SHALL return the matching student with photo, course, and year level
2. WHEN a guard searches by name, THE System SHALL return all matching students ordered by relevance
3. WHEN displaying student details, THE System SHALL show the current day's class schedule with times, rooms, and instructors
4. WHEN displaying student details, THE System SHALL show recent entry history for the last 3 days
5. WHEN a search query is less than 3 characters, THE System SHALL reject it with an error message
6. WHEN a student lookup is performed, THE Activity_Logger SHALL record the search action
7. WHEN no students match the search query, THE System SHALL return an empty result set
8. WHEN multiple students match, THE System SHALL limit results to 10 students

### Requirement 8: Shift Management and Summary

**User Story:** As a guard, I want to see a summary of my shift when I clock out, so that I can review my activity and provide handover information.

#### Acceptance Criteria

1. WHEN a guard clocks in, THE System SHALL create a GuardShift record with shift_start timestamp
2. WHEN a guard clocks out, THE System SHALL update the GuardShift record with shift_end timestamp
3. WHEN calculating shift summary, THE System SHALL count all entries recorded during the shift period
4. WHEN calculating shift summary, THE System SHALL separate entries by scan type (IN/OUT)
5. WHEN calculating shift summary, THE System SHALL count incidents reported during the shift
6. WHEN calculating shift summary, THE System SHALL calculate shift duration in hours
7. WHEN a guard clocks out, THE System SHALL display the shift summary with all statistics
8. WHEN a guard provides a handover note during clock-out, THE System SHALL create a GuardNote associated with the shift

### Requirement 9: Event Capacity Monitoring

**User Story:** As a guard, I want to be alerted when events approach capacity, so that I can manage crowd control and prevent overcrowding.

#### Acceptance Criteria

1. WHEN an event reaches 80% capacity, THE System SHALL calculate the current attendee count
2. WHEN capacity threshold is reached, THE System SHALL create a capacity alert for all on-duty guards
3. WHEN a capacity alert is sent, THE System SHALL include event name, venue, current count, maximum capacity, and percentage
4. WHEN a capacity alert was sent within the last hour, THE System SHALL not send another alert for the same event
5. WHEN an event reaches 100% capacity, THE System SHALL create an urgent priority alert
6. WHEN displaying active events on the dashboard, THE System SHALL show current capacity percentage
7. WHEN an event has maximum_attende of zero, THE System SHALL not perform capacity checks
8. WHEN calculating event capacity, THE System SHALL count only checked-in attendees who have not checked out

### Requirement 10: Mobile-Responsive Dashboard

**User Story:** As a guard using a mobile device, I want the dashboard to be fully functional on my phone, so that I can monitor the gate system while mobile.

#### Acceptance Criteria

1. WHEN the dashboard is accessed on a mobile device, THE System SHALL display a responsive layout optimized for small screens
2. WHEN viewing statistics on mobile, THE System SHALL stack elements vertically for readability
3. WHEN accessing the scanner on mobile, THE System SHALL provide a touch-friendly interface
4. WHEN viewing notifications on mobile, THE System SHALL display them in a scrollable list
5. WHEN the screen width is less than 768 pixels, THE System SHALL hide non-essential UI elements
6. WHEN interacting with buttons on mobile, THE System SHALL provide adequate touch targets (minimum 44x44 pixels)
7. WHEN viewing tables on mobile, THE System SHALL enable horizontal scrolling for wide content
8. WHEN the dashboard auto-refreshes on mobile, THE System SHALL preserve scroll position

### Requirement 11: Notification Priority and Expiration

**User Story:** As a guard, I want urgent notifications to be clearly distinguished from normal ones, so that I can prioritize my response to critical events.

#### Acceptance Criteria

1. WHEN notifications are displayed, THE System SHALL order them by priority (urgent, high, medium, low) then by timestamp
2. WHEN a notification has 'urgent' priority, THE System SHALL display it with a distinct visual indicator
3. WHEN a notification has an expiration time, THE System SHALL automatically hide it after expiration
4. WHEN a notification is marked as read, THE System SHALL update the is_read flag and set read_at timestamp
5. WHEN calculating unread count, THE System SHALL exclude expired notifications
6. WHEN a notification type is 'incident' or 'suspicious', THE System SHALL allow 'urgent' priority
7. WHEN a notification type is 'system', THE System SHALL default to 'medium' priority
8. WHEN displaying notifications, THE System SHALL show the most recent 10 unread notifications

### Requirement 12: Guard Activity Reports

**User Story:** As a supervisor, I want to generate activity reports for guards, so that I can review performance and identify training needs.

#### Acceptance Criteria

1. WHEN generating a guard activity report, THE System SHALL include all logged actions for the specified period
2. WHEN displaying activity logs, THE System SHALL show timestamp, action type, description, and related entities
3. WHEN filtering activity logs, THE System SHALL support filtering by guard, date range, and action type
4. WHEN exporting activity logs, THE System SHALL include all relevant context and metadata
5. WHEN a guard views their own activity log, THE System SHALL show only their actions
6. WHEN a supervisor views activity logs, THE System SHALL show actions from all guards
7. WHEN activity logs are queried, THE System SHALL order them by timestamp descending
8. WHEN displaying activity logs, THE System SHALL paginate results with 50 entries per page

### Requirement 13: Data Validation and Error Handling

**User Story:** As a system administrator, I want robust data validation and error handling, so that the system remains stable and provides clear feedback to users.

#### Acceptance Criteria

1. WHEN creating a notification, THE System SHALL validate that either target_guard is set or broadcast is true
2. WHEN creating a notification with 'urgent' priority, THE System SHALL validate that notification_type is 'incident' or 'suspicious'
3. WHEN creating a GuardNote, THE System SHALL validate that content does not exceed 2000 characters
4. WHEN creating a GuardNotification, THE System SHALL validate that title does not exceed 200 characters
5. WHEN creating a GuardNotification, THE System SHALL validate that message does not exceed 1000 characters
6. WHEN setting expiration time, THE System SHALL validate that expires_at is after created_at
7. WHEN a database operation fails, THE System SHALL log the error and display a user-friendly message
8. WHEN an invalid date range is provided, THE System SHALL return a validation error with details

### Requirement 14: Performance and Scalability

**User Story:** As a system administrator, I want the guard enhancements to perform efficiently under load, so that the system remains responsive during peak usage.

#### Acceptance Criteria

1. WHEN fetching dashboard statistics, THE System SHALL complete the query within 500 milliseconds
2. WHEN creating a broadcast notification, THE System SHALL complete within 2 seconds regardless of guard count
3. WHEN querying entry history, THE System SHALL use database indexes on timestamp and recorded_by fields
4. WHEN calculating performance metrics, THE System SHALL use efficient aggregation queries
5. WHEN displaying recent activity, THE System SHALL limit queries to the last 20 entries
6. WHEN auto-refreshing the dashboard, THE System SHALL use AJAX to fetch only changed data
7. WHEN logging guard activity, THE System SHALL perform the insert asynchronously to avoid blocking
8. WHEN querying notifications, THE System SHALL use indexes on target_guard, is_read, and created_at fields

### Requirement 15: Security and Access Control

**User Story:** As a system administrator, I want strict access controls on guard features, so that only authorized users can access sensitive information.

#### Acceptance Criteria

1. WHEN a non-guard user attempts to access guard features, THE System SHALL deny access with a 403 error
2. WHEN a guard attempts to view another guard's performance metrics, THE System SHALL deny access
3. WHEN a guard attempts to modify activity logs, THE System SHALL prevent the operation
4. WHEN a guard attempts to delete notifications, THE System SHALL allow deletion only of their own notifications
5. WHEN accessing historical data, THE System SHALL enforce role-based date restrictions
6. WHEN a session expires, THE System SHALL redirect to login and clear all cached data
7. WHEN logging guard actions, THE System SHALL capture IP address and device ID for security auditing
8. WHEN a guard account is deactivated, THE System SHALL prevent all guard feature access immediately

## Requirements Traceability

This section maps requirements to design components:

- **Requirement 1** → GuardNotificationService, GuardNotification model
- **Requirement 2** → GuardHistoryManager, access control logic
- **Requirement 3** → GuardPerformanceTracker, GuardPerformanceMetrics
- **Requirement 4** → RealtimeDashboardService, dashboard view
- **Requirement 5** → GuardActivityLogger, GuardActivityLog model
- **Requirement 6** → GuardNotesManager, GuardNote model, GuardNoteRead model
- **Requirement 7** → StudentLookupService, student search views
- **Requirement 8** → GuardShift model, shift management views
- **Requirement 9** → Event capacity checking algorithm, notification service
- **Requirement 10** → Responsive CSS, mobile-optimized templates
- **Requirement 11** → Notification ordering logic, priority validation
- **Requirement 12** → Activity log queries, report generation views
- **Requirement 13** → Model validation, form validation, error handlers
- **Requirement 14** → Database indexes, query optimization, caching
- **Requirement 15** → Permission decorators, role checks, access control
