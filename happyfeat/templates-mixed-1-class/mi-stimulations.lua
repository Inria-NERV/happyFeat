
function initialize(box)

	dofile(box:get_config("${Path_Data}") .. "/plugins/stimulation/lua-stimulator-stim-codes.lua")

	number_of_trials = box:get_setting(2)
	first_class = _G[box:get_setting(3)]
	baseline_duration = box:get_setting(4)
	wait_for_cue_duration = box:get_setting(5)
	display_cue_duration = box:get_setting(6)
	feedback_duration = box:get_setting(7)
	end_of_trial_duration = box:get_setting(8)

end

function process(box)

	local t=0

	-- manages baseline

	box:send_stimulation(1, OVTK_StimulationId_ExperimentStart, t, 0)
	t = t + 2

	box:send_stimulation(1, OVTK_StimulationId_BaselineStart, t, 0)
	box:send_stimulation(1, OVTK_StimulationId_Beep, t, 0)
	t = t + baseline_duration

	box:send_stimulation(1, OVTK_StimulationId_BaselineStop, t, 0)
	box:send_stimulation(1, OVTK_StimulationId_Beep, t, 0)

	-- manages trials

	for i = 1, number_of_trials do

		-- first display cross on screen

		box:send_stimulation(1, OVTK_GDF_Start_Of_Trial, t, 0)
		box:send_stimulation(1, OVTK_GDF_Cross_On_Screen, t, 0)

		t = t + wait_for_cue_duration
		
		-- add 1 s of delay before moving on to the actual trial
		
		t = t + 1

		-- display cue

		box:send_stimulation(1, first_class, t, 0)
		
		t = t + display_cue_duration
		
		-- feedback
		
		box:send_stimulation(1, OVTK_GDF_Feedback_Continuous, t, 0)
		t = t + feedback_duration

		-- ends trial

		box:send_stimulation(1, OVTK_GDF_End_Of_Trial, t, 0)
		t = t + end_of_trial_duration

	end

	-- send end for completeness
	box:send_stimulation(1, OVTK_GDF_End_Of_Session, t, 0)
	t = t + 5

	box:send_stimulation(1, OVTK_StimulationId_Train, t, 0)
	t = t + 1
	
	-- used to cause the acquisition scenario to stop
	box:send_stimulation(1, OVTK_StimulationId_ExperimentStop, t, 0)

end
