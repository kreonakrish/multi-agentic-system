import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  BarControllerChartOptions,
  LineControllerChartOptions,
  DoughnutControllerChartOptions
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

// Common options that apply to all chart types
const commonOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: true,
      text: 'NFL Team Statistics',
      font: {
        size: 16,
        weight: 'bold' as const
      }
    },
  }
};

// Bar chart specific options
export const barChartOptions: ChartOptions<'bar'> & BarControllerChartOptions = {
  ...commonOptions,
  indexAxis: 'y' as const,
  scales: {
    x: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'Average Score',
        font: {
          size: 14,
          weight: 'normal' as const
        }
      }
    },
    y: {
      title: {
        display: true,
        text: 'Teams',
        font: {
          size: 14,
          weight: 'normal' as const
        }
      }
    }
  }
};

// Line chart specific options
export const lineChartOptions: ChartOptions<'line'> & LineControllerChartOptions = {
  ...commonOptions,
  spanGaps: true,
  showLine: true,
  scales: {
    x: {
      title: {
        display: true,
        text: 'Teams',
        font: {
          size: 14,
          weight: 'normal' as const
        }
      }
    },
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'Average Score',
        font: {
          size: 14,
          weight: 'normal' as const
        }
      }
    }
  }
};

// Pie chart specific options
export const pieChartOptions: ChartOptions<'pie'> & DoughnutControllerChartOptions = {
  ...commonOptions,
  circumference: 360,
  rotation: 0,
  cutout: '0%',
  radius: '100%',
  offset: 0,
  spacing: 0,
  animation: {
    animateRotate: true,
    animateScale: true
  }
}; 