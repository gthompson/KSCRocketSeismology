function plotEnsembleSummary(event_metrics, varargin)
%PLOTENSEMBLESUMMARY Plot scalar metrics across the rocket ensemble.

p = inputParser;
p.addRequired('event_metrics', @istable);
p.addParameter('OutputFile', '', @(x) ischar(x) || isstring(x));
p.parse(event_metrics, varargin{:});

figure('Color', 'w');

subplot(3,1,1);
plot(event_metrics.StartTime, event_metrics.MaxInfrasoundAbsAmplitude, 'o-');
ylabel('Max infrasound amp');
grid on;

subplot(3,1,2);
plot(event_metrics.StartTime, event_metrics.MaxSeismicAbsAmplitude, 'o-');
ylabel('Max seismic amp');
grid on;

subplot(3,1,3);
plot(event_metrics.StartTime, event_metrics.MeanInfrasoundPeakFrequencyHz, 'o-');
hold on;
plot(event_metrics.StartTime, event_metrics.MeanSeismicPeakFrequencyHz, 'o-');
ylabel('Mean peak freq. (Hz)');
xlabel('Event time');
legend('Infrasound', 'Seismic', 'Location', 'best');
grid on;

sgtitle('Rocket ensemble summary metrics');

if strlength(string(p.Results.OutputFile)) > 0
    saveas(gcf, char(p.Results.OutputFile));
end
end
