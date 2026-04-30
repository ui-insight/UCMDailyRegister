interface ScheduleFrequencyConfig {
  Is_Daily: boolean;
  Publish_Day_Of_Week: number | null;
  Mode: string;
}

const PYTHON_WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export function formatScheduleFrequency(config: ScheduleFrequencyConfig): string {
  if (config.Is_Daily) return 'Daily (weekdays)';
  if (config.Publish_Day_Of_Week !== null) {
    // Backend schedule configs use Python's date.weekday() convention: Monday=0 ... Sunday=6.
    return `Weekly (${PYTHON_WEEKDAY_NAMES[config.Publish_Day_Of_Week] ?? 'unknown day'})`;
  }
  if (config.Mode === 'winter_break') return 'Custom dates';
  return 'Not published';
}
