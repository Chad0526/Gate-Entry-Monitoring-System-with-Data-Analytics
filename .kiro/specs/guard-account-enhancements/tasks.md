# Implementation Plan: Guard Account Enhancements

## Overview

This implementation plan breaks down the guard account enhancements into incremental, testable tasks. The feature adds real-time notifications, 7-day historical access, performance metrics, improved dashboard UI, comprehensive activity logging, and shift handover tools for guards. Implementation follows a bottom-up approach: database models first, then service components, then views and templates, ensuring each layer can be tested before building the next.

## Tasks

- [x] 1. Set up database models and migrations
  - [x] 1.1 Create GuardNotification model
    - Define model with all fields: notification_type, priority, title, message, target_guard, broadcast, related fields, is_read, read_at, created_at, expires_at
    - Add database indexes on notification_type, is_read, target_guard, created_at
    - Implement model validation: either target_guard or broadcast must be set, priority 'urgent' requires incident/suspicious type, expires_at > created_at
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 13.1, 13.2, 13.4, 13.5, 13.6_
  
  - [ ]* 1.2 Write property test for GuardNotification model
    - **Property 18: Notification Validation Rules**
    - **Validates: Requirements 13.1, 13.2, 11.6**
  
  - [x] 1.3 Create GuardNote model
    - Define model with fields: guard, shift, priority, content, created_at, updated_at
    - Add foreign keys to User (guard) and GuardShift (shift, nullable)
    - Implement validation: content max 2000 chars, guard must be in Guard group
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 13.3_
  
  - [x] 1.4 Create GuardNoteRead model
    - Define model with fields: note, guard, read_at
    - Add unique constraint on (note, guard) combination
    - Add foreign keys to GuardNote and User
    - _Requirements: 6.4, 6.5_
  
  - [x] 1.5 Create GuardActivityLog model
    - Define model with fields: guard, action_type, description, related fields (entry, incident, shift, student), device_id, ip_address, metadata, timestamp
    - Add database indexes on guard, action_type, timestamp
    - Implement validation: description max 500 chars, guard must be in Guard group, at least one related field should be set
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 15.3, 15.7_
  
  - [ ]* 1.6 Write property test for GuardActivityLog model
    - **Property 3: Activity Log Immutability**
    - **Validates: Requirements 5.8, 15.3**
  
  - [x] 1.7 Generate and apply database migrations
    - Create migrations for all new models
    - Apply migrations to database
    - Verify tables created with correct indexes
    - _Requirements: All model-related requirements_

- [x] 2. Implement core service components
  - [x] 2.1 Create GuardNotificationService class
    - Implement create_incident_alert() method with priority logic based on incident reason
    - Implement create_capacity_alert() method with event details
    - Implement create_shift_reminder() method
    - Implement create_suspicious_activity_alert() method
    - Implement get_unread_notifications() method with filtering by guard and is_read=False
    - Implement mark_as_read() method to update is_read and read_at
    - Handle broadcast notifications by creating one notification per on-duty guard
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_
  
  - [ ]* 2.2 Write property test for GuardNotificationService
    - **Property 1: Broadcast Notification Delivery**
    - **Validates: Requirements 1.1, 1.2, 6.2, 9.2**
  
  - [ ]* 2.3 Write property test for notification read state
    - **Property 7: Notification Read State Tracking**
    - **Validates: Requirements 1.5**
  
  - [x] 2.4 Create GuardActivityLogger class
    - Implement log_scan() method with device_id and ip_address capture
    - Implement log_override() method with reason and original_result in metadata
    - Implement log_incident_creation() method
    - Implement log_shift_action() method for clock in/out
    - Implement log_note_creation() method
    - Implement get_guard_activity() method with date range filtering
    - Implement get_shift_activity() method
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_
  
  - [ ]* 2.5 Write property test for GuardActivityLogger
    - **Property 11: Activity Logging Completeness**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**
  
  - [x] 2.6 Create GuardHistoryManager class
    - Implement get_entries_last_7_days() with role-based access control
    - Implement get_visitor_history_last_7_days() method
    - Implement get_incidents_last_7_days() method
    - Implement get_weekly_summary() aggregation method
    - Implement get_monthly_summary() aggregation method
    - Implement can_access_date() method with 7-day restriction for guards
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [ ]* 2.7 Write property test for GuardHistoryManager
    - **Property 2: Role-Based Historical Access Control**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.6, 15.5**
  
  - [x] 2.8 Create GuardPerformanceTracker class
    - Implement get_shift_metrics() method
    - Implement calculate_scans_per_hour() method
    - Implement calculate_accuracy_rate() method (successful / total)
    - Implement get_incident_response_time() method
    - Implement get_performance_summary() method with all metrics
    - Ensure all metrics are non-negative and accuracy_rate is 0-100
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [ ]* 2.9 Write property test for GuardPerformanceTracker
    - **Property 6: Performance Metrics Valid Ranges**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.6, 3.7**

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement dashboard and real-time services
  - [x] 4.1 Create RealtimeDashboardService class
    - Implement get_current_stats() method returning all dashboard metrics
    - Implement get_currently_inside_count() method
    - Implement get_hourly_activity_chart() method with 24 data points (hours 0-23)
    - Implement get_recent_activity_feed() method limited to 20 entries
    - Implement get_shift_summary() method
    - Implement get_active_alerts() method
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_
  
  - [ ]* 4.2 Write property test for currently inside count
    - **Property 10: Currently Inside Count Accuracy**
    - **Validates: Requirements 4.1**
  
  - [ ]* 4.3 Write property test for hourly activity chart
    - **Property 28: Hourly Activity Chart Completeness**
    - **Validates: Requirements 4.4**
  
  - [x] 4.4 Create GuardNotesManager class
    - Implement create_note() method with priority and shift association
    - Implement get_recent_notes() method limited to specified count
    - Implement get_unread_notes() method using GuardNoteRead tracking
    - Implement mark_note_read() method creating GuardNoteRead record
    - Implement search_notes() method with date range and priority filters
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_
  
  - [ ]* 4.5 Write property test for GuardNotesManager
    - **Property 12: Guard Note Shift Association**
    - **Validates: Requirements 6.1, 6.7**
  
  - [x] 4.6 Create StudentLookupService class
    - Implement lookup_by_id() method
    - Implement lookup_by_name() method with result limiting to 10 students
    - Implement get_current_schedule() method from load slip
    - Implement get_today_schedule() method
    - Implement verify_class_time() method
    - Implement get_recent_entries() method with configurable days parameter
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [ ]* 4.7 Write property test for StudentLookupService
    - **Property 13: Student Lookup Result Limiting**
    - **Validates: Requirements 7.8**

- [x] 5. Implement event capacity monitoring
  - [x] 5.1 Create event capacity checking algorithm
    - Implement check_event_capacity_and_alert() function
    - Calculate current attendee count (checked_in_at not null, checked_out_at null)
    - Calculate capacity percentage
    - Check 80% threshold and create capacity alert
    - Implement rate limiting (one alert per hour per event)
    - Escalate to urgent priority at 100% capacity
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_
  
  - [ ]* 5.2 Write property test for event capacity calculation
    - **Property 15: Event Capacity Calculation**
    - **Validates: Requirements 9.1, 9.8**
  
  - [ ]* 5.3 Write property test for capacity alert rate limiting
    - **Property 16: Capacity Alert Rate Limiting**
    - **Validates: Requirements 9.4**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement view functions
  - [x] 7.1 Create guard_dashboard_view() function
    - Check user authentication and Guard group membership
    - Get current shift information
    - Call RealtimeDashboardService.get_current_stats()
    - Get unread notifications and notes
    - Render dashboard template with context
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 15.1_
  
  - [x] 7.2 Create guard_entry_list_view() function
    - Check user authentication and role
    - Extract date filters from request
    - Apply 7-day restriction for guards using GuardHistoryManager
    - Display warning message if date adjusted
    - Paginate results (max 500 per page)
    - Render entry list template
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 15.1, 15.5_
  
  - [x] 7.3 Create guard_notifications_view() function
    - Get all notifications for current guard
    - Order by priority (urgent, high, medium, low) then timestamp
    - Filter out expired notifications
    - Limit to most recent 10 unread for navbar
    - Render notifications template
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_
  
  - [x] 7.4 Create mark_notification_read_view() function
    - Validate notification belongs to current guard
    - Call GuardNotificationService.mark_as_read()
    - Return JSON response
    - _Requirements: 1.5, 15.4_
  
  - [x] 7.5 Create guard_performance_view() function
    - Check user can only view own metrics
    - Get date range from request (default to current month)
    - Call GuardPerformanceTracker.get_performance_summary()
    - Render performance metrics template
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 15.2_
  
  - [x] 7.6 Create guard_clock_in_view() function
    - Create GuardShift record with shift_start
    - Log shift start using GuardActivityLogger
    - Redirect to dashboard
    - _Requirements: 8.1_
  
  - [x] 7.7 Create guard_clock_out_view() function
    - Get active shift for current guard
    - Get handover note from form if provided
    - Create GuardNote if handover note provided
    - Calculate shift summary using calculate_shift_summary()
    - Update GuardShift with shift_end timestamp
    - Log shift end using GuardActivityLogger
    - Render shift summary template
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 7.8 Create quick_student_lookup_view() function
    - Validate search query length (min 3 chars)
    - Call StudentLookupService methods
    - Get today's schedule and recent entries (last 3 days)
    - Log lookup action using GuardActivityLogger
    - Return JSON response with results
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [x] 7.9 Create dashboard_stats_api_view() function
    - AJAX endpoint for auto-refresh
    - Call RealtimeDashboardService.get_current_stats()
    - Return JSON response with stats
    - _Requirements: 4.2, 4.8_
  
  - [x] 7.10 Create guard_activity_log_view() function
    - Check user role (guards see own logs, supervisors see all)
    - Get date range and action type filters from request
    - Query GuardActivityLog with filters
    - Order by timestamp descending
    - Paginate results (50 per page)
    - Render activity log template
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 15.2_
  
  - [ ]* 7.11 Write integration tests for view functions
    - Test authentication and authorization
    - Test role-based access control
    - Test date range restrictions
    - Test pagination
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8_

- [x] 8. Create context processor for notifications
  - [x] 8.1 Implement guard_notifications_context() function
    - Check if user is authenticated and in Guard group
    - Get unread notifications for current guard
    - Calculate unread count
    - Check for urgent notifications (has_urgent flag)
    - Order notifications by priority then timestamp
    - Limit to 10 most recent unread
    - Return context dict with guard_notifications, unread_count, has_urgent
    - _Requirements: 1.6, 11.1, 11.8_
  
  - [ ]* 8.2 Write property test for unread notification count
    - **Property 30: Unread Notification Count Accuracy**
    - **Validates: Requirements 1.6**
  
  - [x] 8.3 Register context processor in settings
    - Add to TEMPLATES context_processors list
    - _Requirements: 1.6_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create templates for guard dashboard
  - [x] 10.1 Create guard_dashboard.html template
    - Display current shift information (if active)
    - Show currently inside count
    - Display hourly activity chart (24 hours)
    - Show recent activity feed (last 20 entries)
    - Display active events with capacity percentages
    - Show quick actions (clock in/out, scanner, lookup)
    - Add auto-refresh JavaScript (30 second interval)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_
  
  - [x] 10.2 Create notification panel partial template
    - Display notifications ordered by priority
    - Show visual indicator for urgent notifications
    - Display notification badge with unread count
    - Add mark-as-read functionality
    - Filter out expired notifications
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 11.1, 11.2, 11.3, 11.4, 11.5_
  
  - [x] 10.3 Create guard_entry_list.html template
    - Display entry table with student info, timestamp, scan type, status
    - Add date range filter controls
    - Add search box for student lookup
    - Add scan type filter dropdown
    - Show warning message if date range adjusted
    - Implement pagination controls
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [x] 10.4 Create guard_performance.html template
    - Display total scans, successful scans, denied scans
    - Show accuracy rate as percentage
    - Display scans per hour metric
    - Show incidents reported and overrides made
    - Display shift statistics (shifts worked, total hours)
    - Add date range selector
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [x] 10.5 Create shift_summary.html template
    - Display shift duration in hours
    - Show total entries during shift
    - Break down entries by type (IN/OUT)
    - Display incidents reported during shift
    - Show handover note if provided
    - _Requirements: 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 10.6 Create student_lookup_modal.html template
    - Display student photo, ID, name, course, year level
    - Show today's class schedule with times and rooms
    - Display recent entry history (last 3 days)
    - Add search input with min 3 character validation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  
  - [x] 10.7 Create guard_activity_log.html template
    - Display activity log table with timestamp, action type, description
    - Show related entities (student, incident, shift)
    - Add filters for date range and action type
    - Implement pagination (50 per page)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

- [x] 11. Implement mobile-responsive CSS
  - [x] 11.1 Add responsive breakpoints and mobile styles
    - Add media queries for screens < 768px
    - Stack dashboard elements vertically on mobile
    - Make notification panel scrollable on mobile
    - Ensure touch targets are minimum 44x44 pixels
    - Enable horizontal scrolling for wide tables
    - Hide non-essential UI elements on mobile
    - Preserve scroll position on auto-refresh
    - Optimize scanner interface for touch
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

- [x] 12. Add URL routing and wire components
  - [x] 12.1 Create URL patterns for all guard views
    - Add route for guard_dashboard_view
    - Add route for guard_entry_list_view
    - Add route for guard_notifications_view
    - Add route for mark_notification_read_view
    - Add route for guard_performance_view
    - Add route for guard_clock_in_view
    - Add route for guard_clock_out_view
    - Add route for quick_student_lookup_view
    - Add route for dashboard_stats_api_view
    - Add route for guard_activity_log_view
    - _Requirements: All view-related requirements_
  
  - [x] 12.2 Add permission decorators to views
    - Apply @login_required to all guard views
    - Apply @user_passes_test(is_guard) to guard-specific views
    - Apply @user_passes_test(is_supervisor_or_admin) to admin views
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8_
  
  - [x] 12.3 Integrate notification creation into existing incident reporting
    - Update incident report view to call GuardNotificationService.create_incident_alert()
    - Add broadcast parameter for incident alerts
    - _Requirements: 1.1, 1.2_
  
  - [x] 12.4 Integrate activity logging into existing scanner
    - Update scanner view to call GuardActivityLogger.log_scan()
    - Capture device_id and ip_address from request
    - _Requirements: 5.1, 15.7_
  
  - [x] 12.5 Integrate capacity checking into event attendance
    - Update event attendance scanner to call check_event_capacity_and_alert()
    - Trigger capacity alerts at 80% and 100%
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [ ] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Integration tests validate end-to-end flows
- Implementation uses Python with Django framework
- Database indexes are critical for performance (Requirements 14.3, 14.8)
- All guard actions must be logged for audit trail (Requirement 5.8)
- Role-based access control enforced at view level (Requirements 15.1-15.8)
