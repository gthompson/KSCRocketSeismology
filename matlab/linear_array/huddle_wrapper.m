%% huddle_wrapper.m
% Convenience runner for the huddle linear-array workflow.

run_import = true;
run_analysis = true;
run_figures = true;

if run_import
    run('10_import_huddle_data.m');
end

if run_analysis
    run('20_analyze_huddle_xcorr.m');
end

if run_figures
    run('30_plot_huddle_results.m');
end
