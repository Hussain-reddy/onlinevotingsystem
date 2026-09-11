function confirmVote() {

    const selectedCandidate =
        document.querySelector(
            'input[name="candidate"]:checked'
        );

    if (!selectedCandidate) {
        alert("Please select a candidate.");
        return false;
    }

    return confirm(
        "Are you sure you want to submit your vote? You cannot vote again."
    );
}