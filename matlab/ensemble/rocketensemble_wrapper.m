%% rocketensemble_wrapper.m
% Convenience runner for the rocket launch ensemble workflow.

run_preprocess = true;
run_analysis = true;
run_plots = true;

if run_preprocess
    run('10_preprocess_rocketmaster.m');
end

if run_analysis
    run('20_analyze_ensemble.m');
end

if run_plots
    run('30_plot_ensemble_results.m');
end
